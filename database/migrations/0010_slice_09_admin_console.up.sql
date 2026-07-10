alter table disputes
    drop constraint if exists disputes_resolution_type_future_check;

alter table disputes
    drop constraint if exists disputes_resolution_type_check;

alter table disputes
    add constraint disputes_resolution_type_check check (
        resolution_type is null
        or resolution_type in (
            'remitter_favored',
            'business_favored',
            'cancelled',
            'completed',
            'keep_under_review'
        )
    );

alter table disputes
    drop constraint if exists disputes_admin_resolution_required_check;

alter table disputes
    add constraint disputes_admin_resolution_required_check check (
        (
            status not in ('resolved', 'cancelled')
        )
        or (
            resolution_type is not null
            and resolution_reason is not null
            and (
                (status = 'resolved' and resolved_by_admin_id is not null and resolved_at is not null)
                or (status = 'cancelled' and cancelled_at is not null)
            )
        )
    );

alter table dispute_events
    drop constraint if exists dispute_events_event_type_check;

alter table dispute_events
    add constraint dispute_events_event_type_check check (
        event_type in (
            'dispute_opened',
            'dispute_status_changed',
            'dispute_note_added',
            'dispute_resolved',
            'dispute_cancelled',
            'dispute_message_created',
            'dispute_marked_in_review'
        )
    );
