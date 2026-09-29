"""Opt-in PostgreSQL 17 drill. Never accepts a URL or an existing data directory."""

from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(r"C:\Program Files\PostgreSQL\17\bin")
PORT = 56465
USER = "nodo_synthetic_drill"
INDEXES = {
    "credits_ledger_release_ad_unique_idx",
    "credits_ledger_consume_order_unique_idx",
    "credits_ledger_expire_ad_unique_idx",
}
MIGRATIONS = ROOT / "database" / "migrations"


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def main():
    require(sys.argv[1:] == ["--run-synthetic-only"], "EXPLICIT_OPT_IN_REQUIRED")
    require(os.name == "nt", "WINDOWS_ONLY")
    inherited = {
        key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ
    }
    os.environ.clear()
    os.environ.update(inherited)
    # Native PostgreSQL needs the Windows shell even with an otherwise empty environment.
    os.environ["COMSPEC"] = r"C:\WINDOWS\System32\cmd.exe"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import psycopg
    from psycopg.rows import dict_row

    sys.path.insert(0, str(ROOT / "apps" / "api"))
    from app.core.errors import ApiError
    from app.modules.ads.postgres_credit_holds import PostgresAdCreditHoldsMixin

    # Only these audited modules are imported, never main/config or a .env loader.
    require("app.core.config" not in sys.modules, "CONFIG_IMPORT_FORBIDDEN")

    def guard(event, args):
        if event.startswith("socket.") and event not in {
            "socket.__new__",
            "socket.bind",
        }:
            raise RuntimeError("EXTERNAL_NETWORK_FORBIDDEN")
        if event == "subprocess.Popen":
            require(
                isinstance(args[0], str)
                and Path(args[0]).resolve()
                in {BIN / (name + ".exe") for name in ("postgres", "initdb", "pg_ctl")},
                "PROCESS_FORBIDDEN",
            )
        if event == "os.system":
            raise RuntimeError("PROCESS_FORBIDDEN")
        if event == "open" and isinstance(args[0], (str, bytes)):
            require(
                not Path(os.fsdecode(args[0])).name.startswith(".env"),
                "ENV_FILE_FORBIDDEN",
            )

    sys.addaudithook(guard)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", PORT))
    folder = Path(
        tempfile.mkdtemp(
            prefix="nodo-credit-0065-", dir=r"C:\Users\carlo\AppData\Local\Temp"
        )
    )
    data = folder / "data"
    password_file = folder / "synthetic-password.txt"
    password = secrets.token_urlsafe(32)
    password_file.write_text(password + "\n", encoding="ascii")
    os.environ.update(
        TEMP=str(folder),
        TMP=str(folder),
        PGPASSFILE=str(folder / "unused-passfile"),
        PGSERVICEFILE=str(folder / "unused-servicefile"),
    )
    result = {
        "synthetic_only": True,
        "directory": str(folder),
        "port": PORT,
        "checks": [],
        "process_results": [],
        "migrations": [],
        "status": "RUNNING",
        "stopped": False,
    }
    deadline = time.monotonic() + 300
    started = False
    stage = "preflight"
    database = "postgres"

    def remaining():
        seconds = deadline - time.monotonic()
        require(seconds > 0, "DRILL_DEADLINE")
        return min(seconds, 40)

    def command(name, args, *, closing=False):
        require(name in {"postgres", "initdb", "pg_ctl"}, "PROCESS_FORBIDDEN")
        log = folder / (name + "-" + stage + ".log")
        # pg_ctl descendants inherit handles on Windows; files avoid waiting for pipe EOF.
        with log.open("wb") as stream:
            output = subprocess.run(
                [str(BIN / (name + ".exe")), *args],
                executable=str(BIN / (name + ".exe")),
                cwd=folder,
                env=dict(os.environ),
                stdin=subprocess.DEVNULL,
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=40 if closing else remaining(),
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
        result["process_results"].append(
            {"stage": stage, "program": name, "returncode": output.returncode}
        )
        # Logs contain only this fresh cluster's synthetic records. Never echo raw errors.
        output.stdout = log.read_text(encoding="utf-8", errors="replace")
        return output

    def connect():
        remaining()
        conn = psycopg.connect(
            host="127.0.0.1",
            hostaddr="127.0.0.1",
            port=PORT,
            dbname=database,
            user=USER,
            password=password,
            connect_timeout=3,
            sslmode="disable",
            gssencmode="disable",
            application_name="nodo_synthetic_0065",
            row_factory=dict_row,
            options="-c statement_timeout=12000 -c lock_timeout=10000 "
            "-c idle_in_transaction_session_timeout=20000",
        )
        identity = conn.execute(
            "select current_setting('data_directory') as path, current_user as usr, "
            "current_setting('server_version_num')::int as version, inet_server_port() as port, "
            "current_setting('transaction_isolation') as isolation"
        ).fetchone()
        require(Path(identity["path"]).resolve() == data.resolve(), "WRONG_CLUSTER")
        require(identity["usr"] == USER and identity["port"] == PORT, "WRONG_ENDPOINT")
        require(identity["version"] == 170010, "UNEXPECTED_SERVER_VERSION")
        require(identity["isolation"] == "read committed", "UNEXPECTED_ISOLATION")
        conn.commit()
        return conn

    def passed(name):
        result["checks"].append(name)
        print("PASS", name, flush=True)

    def migration(conn, direction):
        path = MIGRATIONS / ("0065_credit_hold_idempotency." + direction + ".sql")
        conn.execute(path.read_text(encoding="utf-8"))

    def index_state(conn):
        rows = conn.execute(
            "select c.relname, i.indisunique, i.indisvalid, pg_get_indexdef(i.indexrelid) as definition "
            "from pg_index i join pg_class c on c.oid=i.indexrelid where c.relname = any(%s) "
            "order by c.relname",
            (sorted(INDEXES),),
        ).fetchall()
        return rows

    def snapshot(conn):
        return conn.execute(
            "select jsonb_build_object('ledger',(select jsonb_agg(to_jsonb(x) order by id) from credits_ledger x),"
            "'wallets',(select jsonb_agg(to_jsonb(x) order by id) from credit_wallets x),"
            "'ads',(select jsonb_agg(to_jsonb(x) order by id) from ads x)) as content"
        ).fetchone()["content"]

    def seed(conn):
        user, business, method, ad_id, hold, order = (str(uuid4()) for _ in range(6))
        conn.execute(
            "insert into users(id,first_name) values (%s,'Synthetic')", (user,)
        )
        conn.execute(
            "insert into businesses(id,owner_user_id,business_name) values (%s,%s,'Synthetic drill')",
            (business, user),
        )
        conn.execute(
            "insert into business_payment_methods(id,business_id,method_type,account_value,account_masked,holder_name) "
            "values (%s,%s,'zelle','synthetic@example.invalid','synthetic','Synthetic')",
            (method, business),
        )
        conn.execute(
            "insert into credit_wallets(business_id,available_credits,blocked_credits,consumed_credits) values (%s,10,4,0)",
            (business,),
        )
        conn.execute(
            "insert into ads(id,business_id,payment_method_id,payment_method,delivery_method,rate_bs_per_usd,"
            "amount_min_usd,amount_max_usd,required_credits,status) values (%s,%s,%s,'zelle','pago_movil_ve',1,20,100,2,'draft')",
            (ad_id, business, method),
        )
        conn.execute(
            "insert into credits_ledger(id,business_id,type,amount,available_before,available_after,blocked_before,"
            "blocked_after,consumed_before,consumed_after,related_ad_id,reason,source,reference_type,reference_id) "
            "values (%s,%s,'hold',2,12,10,2,4,0,0,%s,'synthetic','synthetic','ad',%s)",
            (hold, business, ad_id, ad_id),
        )
        conn.execute(
            "update ads set credit_hold_ledger_id=%s where id=%s", (hold, ad_id)
        )
        conn.execute(
            "insert into orders(id,public_order_code,ad_id,business_id,remitter_user_id,status,amount_usd,rate_snapshot,"
            "amount_bs_calculated,business_name_snapshot,payment_method_snapshot,delivery_method_snapshot,"
            "min_amount_snapshot,max_amount_snapshot,payment_instructions_snapshot,receiver_data_json,"
            "payment_report_deadline_at,expires_at) values (%s,%s,%s,%s,%s,'waiting_payment',50,1,50,'Synthetic',"
            "'zelle','pago_movil_ve',20,100,'{}','{}',now()+interval '1 hour',now()+interval '1 hour')",
            (order, "SYN-" + order, ad_id, business, user),
        )
        return (
            SimpleNamespace(
                id=ad_id,
                business_id=business,
                required_credits=2,
                credit_hold_ledger_id=hold,
            ),
            user,
            order,
        )

    def duplicate(conn, fixture, kind):
        ad, user, order = fixture
        conn.execute(
            "insert into credits_ledger(business_id,type,amount,available_before,available_after,blocked_before,"
            "blocked_after,consumed_before,consumed_after,related_ad_id,related_order_id,reason,source,reference_type,reference_id,created_by) "
            "values (%s,%s,2,10,10,4,2,0,2,%s,%s,'synthetic','synthetic',%s,%s,%s)",
            (
                ad.business_id,
                kind,
                ad.id,
                order if kind == "consume" else None,
                "order" if kind == "consume" else "ad",
                order if kind == "consume" else ad.id,
                user,
            ),
        )

    repo = PostgresAdCreditHoldsMixin()

    def invoke(conn, fixture, kind):
        ad, user, order = fixture
        if kind == "consume":
            return repo.consume_hold_for_order_in_transaction(
                conn, ad=ad, order_id=order, created_by=user
            )
        return getattr(repo, kind + "_hold_in_transaction")(
            conn, ad=ad, created_by=user
        )

    def race(kind):
        with connect() as setup:
            fixture = seed(setup)
        barrier = threading.Barrier(2, timeout=8)
        release = threading.Event()
        pids, outcomes = queue.Queue(), queue.Queue()

        class SynchronizedConnection:
            def __init__(self, conn):
                self.conn = conn

            def execute(self, sql, params=None):
                if "for update" in sql.lower():
                    barrier.wait()
                    cursor = self.conn.execute(sql, params)
                    require(release.wait(8), "OBSERVER_TIMEOUT")
                    return cursor
                return self.conn.execute(sql, params)

        def worker():
            try:
                with connect() as conn:
                    pids.put(conn.info.backend_pid)
                    value = invoke(SynchronizedConnection(conn), fixture, kind)
                outcomes.put("changed" if value is not None else "noop")
            except ApiError as exc:
                outcomes.put((exc.code, exc.status_code))
            except Exception as exc:  # noqa: BLE001 - propagate a redacted failure to the parent.
                outcomes.put((type(exc).__name__, getattr(exc, "sqlstate", None)))

        threads = [threading.Thread(target=worker) for _ in range(2)]
        try:
            for thread in threads:
                thread.start()
            worker_pids = [pids.get(timeout=8), pids.get(timeout=8)]
            require(len(set(worker_pids)) == 2, "DISTINCT_CONNECTIONS_REQUIRED")
            with connect() as observer:
                observed = False
                until = time.monotonic() + 6
                while time.monotonic() < until:
                    blocked = observer.execute(
                        "select count(*) as n from pg_stat_activity where pid=any(%s) "
                        "and cardinality(pg_blocking_pids(pid)) > 0",
                        (worker_pids,),
                    ).fetchone()["n"]
                    if blocked:
                        observed = True
                        break
                    time.sleep(0.025)
                require(observed, "REAL_LOCK_WAIT_NOT_OBSERVED")
        finally:
            release.set()
            for thread in threads:
                if thread.ident is not None:
                    thread.join(15)
            require(
                not any(thread.is_alive() for thread in threads), "WORKER_NOT_CLOSED"
            )
        results = [outcomes.get_nowait(), outcomes.get_nowait()]
        expected = [
            "changed",
            ("CREDIT_ALREADY_CONSUMED", 409) if kind == "consume" else "noop",
        ]
        require(
            sorted(map(str, results)) == sorted(map(str, expected)),
            "RACE_RESULT_MISMATCH",
        )
        with connect() as conn:
            ad = fixture[0]
            wallet = conn.execute(
                "select * from credit_wallets where business_id=%s", (ad.business_id,)
            ).fetchone()
            balances = tuple(
                wallet[k]
                for k in ("available_credits", "blocked_credits", "consumed_credits")
            )
            require(
                balances == ((12, 2, 0) if kind == "release" else (10, 2, 2)),
                "DOUBLE_WALLET_EFFECT",
            )
            ledger = conn.execute(
                "select * from credits_ledger where business_id=%s and type=%s",
                (ad.business_id, kind),
            ).fetchall()
            require(
                len(ledger) == 1 and ledger[0]["amount"] == 2, "DOUBLE_LEDGER_EFFECT"
            )
            if kind != "release":
                row = conn.execute("select * from ads where id=%s", (ad.id,)).fetchone()
                require(
                    row["status"] == "archived"
                    and row["credit_consumed_ledger_id"] == ledger[0]["id"],
                    "AD_LEDGER_LINK",
                )
        passed(kind + "_actual_lock_wait_single_effect")

    try:
        version = command("postgres", ["--version"])
        require(
            version.returncode == 0 and "PostgreSQL) 17.10" in version.stdout,
            "BINARY_VERSION",
        )
        result["postgres_version"] = version.stdout.strip()
        stage = "initdb"
        output = command(
            "initdb",
            [
                "-D",
                str(data),
                "--encoding=UTF8",
                "--locale=C",
                "--auth=scram-sha-256",
                "--username=" + USER,
                "--pwfile=" + str(password_file),
            ],
        )
        require(output.returncode == 0, "INITDB_FAILED")
        (data / "pg_hba.conf").write_text(
            "host all "
            + USER
            + " 127.0.0.1/32 scram-sha-256\nhost all all 0.0.0.0/0 reject\nhost all all ::/0 reject\n",
            encoding="ascii",
        )
        stage = "start"
        output = command(
            "pg_ctl",
            [
                "-D",
                str(data),
                "-l",
                str(folder / "postgres.log"),
                "-w",
                "-t",
                "20",
                "-o",
                "-h 127.0.0.1 -p 56465 -c shared_buffers=16MB -c max_connections=10",
                "start",
            ],
        )
        started = (data / "postmaster.pid").exists()
        require(output.returncode == 0 and started, "START_FAILED")
        with connect() as conn:
            conn.autocommit = True
            conn.execute("create database nodo_synthetic_0065")
        database = "nodo_synthetic_0065"
        passed("fresh_cluster_identity_and_loopback")

        files = sorted(MIGRATIONS.glob("*.up.sql"))
        require(
            [int(p.name[:4]) for p in files] == list(range(1, 66)),
            "MIGRATION_INVENTORY",
        )
        for path in files[:64]:
            require(
                re.fullmatch(r"[0-9]{4}_[A-Za-z0-9_]+\.up\.sql", path.name),
                "MIGRATION_NAME",
            )
            stage = path.name
            with connect() as conn:
                conn.execute(path.read_text(encoding="utf-8"))
            result["migrations"].append(
                {
                    "name": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        passed("schema_0001_through_0064")

        stage = "migration_roundtrip"
        with connect() as conn:
            seed(conn)
            before = snapshot(conn)
            require(not index_state(conn), "INDEXES_ALREADY_PRESENT")
            migration(conn, "up")
            original_indexes = index_state(conn)
            require(
                {r["relname"] for r in original_indexes} == INDEXES, "INDEX_INVENTORY"
            )
            require(
                all(r["indisunique"] and r["indisvalid"] for r in original_indexes),
                "INDEX_VALIDITY",
            )
            require(snapshot(conn) == before, "UP_CHANGED_DATA")
        with connect() as conn:
            migration(conn, "down")
            require(
                not index_state(conn) and snapshot(conn) == before, "DOWN_CHANGED_DATA"
            )
        with connect() as conn:
            migration(conn, "up")
            require(
                index_state(conn) == original_indexes and snapshot(conn) == before,
                "REAPPLY_CHANGED_DATA",
            )
        passed("0065_up_down_up_preserves_fixture_records")

        for kind in ("release", "consume", "expire"):
            stage = "preexisting_duplicates_" + kind
            with connect() as conn:
                migration(conn, "down")
                fixture = seed(conn)
                duplicate(conn, fixture, kind)
                duplicate(conn, fixture, kind)
                before = snapshot(conn)
                try:
                    with conn.transaction():
                        migration(conn, "up")
                except psycopg.errors.UniqueViolation:
                    pass
                else:
                    raise RuntimeError("DUPLICATES_ACCEPTED")
                require(
                    not index_state(conn) and snapshot(conn) == before,
                    "FAILED_MIGRATION_PARTIAL_EFFECT",
                )
                conn.rollback()
            passed("preexisting_" + kind + "_duplicates_rejected_atomically")

            stage = "unique_constraint_" + kind
            with connect() as conn:
                require(len(index_state(conn)) == 3, "ROLLBACK_LOST_INDEXES")
                fixture = seed(conn)
                duplicate(conn, fixture, kind)
                before = snapshot(conn)
                try:
                    with conn.transaction():
                        conn.execute(
                            "update credit_wallets set available_credits=available_credits+1 where business_id=%s",
                            (fixture[0].business_id,),
                        )
                        duplicate(conn, fixture, kind)
                except psycopg.errors.UniqueViolation:
                    pass
                else:
                    raise RuntimeError("UNIQUE_GUARD_MISSING")
                require(snapshot(conn) == before, "FAILED_WRITE_PARTIAL_EFFECT")
            passed(kind + "_unique_guard_and_transaction_rollback")
            stage = "concurrency_" + kind
            race(kind)

        result["status"] = "PASS"
    except Exception as exc:  # noqa: BLE001 - fail closed, record stage, then stop our cluster.
        result.update(
            status="FAIL",
            failed_stage=stage,
            error_type=type(exc).__name__,
            sqlstate=getattr(exc, "sqlstate", None),
        )
        if isinstance(exc, RuntimeError) and re.fullmatch(r"[A-Z_]+", str(exc)):
            result["error_code"] = str(exc)
    finally:
        stage = "stop"
        try:
            if started or (data / "postmaster.pid").exists():
                output = command(
                    "pg_ctl",
                    ["-D", str(data), "-m", "fast", "-w", "-t", "20", "stop"],
                    closing=True,
                )
                status = command("pg_ctl", ["-D", str(data), "status"], closing=True)
                result["stopped"] = (
                    output.returncode == 0
                    and status.returncode == 3
                    and not (data / "postmaster.pid").exists()
                )
            else:
                result["stopped"] = True
        except Exception as exc:  # noqa: BLE001 - a stop failure must survive in the result.
            result["stop_error_type"] = type(exc).__name__
        if not result["stopped"]:
            result["status"] = "FAIL_STOP"
        result["elapsed_seconds"] = round(300 - (deadline - time.monotonic()), 2)
        (folder / "result.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result["status"] == "PASS" and result["stopped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
