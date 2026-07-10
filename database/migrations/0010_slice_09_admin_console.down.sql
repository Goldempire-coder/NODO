alter table dispute_events
    drop constraint if exists dispute_events_event_type_check;

delete from dispute_events
where event_type = 'dispute_marked_in_review';

alter table dispute_events
    add constraint dispute_events_event_type_check check (
        event_type in (
            'dispute_opened',
            'dispute_status_changed',
            'dispute_note_added',
            'dispute_resolved',
            'dispute_cancelled',
            'dispute_message_created'
        )
    );

alter table disputes
    drop constraint if exists disputes_admin_resolution_required_check;

alter table disputes
    drop constraint if exists disputes_resolution_type_check;

update disputes
set
    resolution_type = null,
    resolution_reason = null,
    resolved_by_admin_id = null,
    resolved_at = null
where resolution_type in (
    'remitter_favored',
    'business_favored',
    'cancelled',
    'completed',
    'keep_under_review'
);

alter table disputes
    add constraint disputes_resolution_type_future_check check (
        resolution_type is null
        or resolution_type in ('future_admin_resolution')
    );
