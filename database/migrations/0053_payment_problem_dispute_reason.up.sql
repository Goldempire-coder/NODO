alter table disputes
    drop constraint if exists disputes_reason_check;

alter table disputes
    add constraint disputes_reason_check check (
        reason in (
            'business_no_payment_confirmation',
            'business_confirmed_payment_but_not_delivered',
            'payment_not_received_or_incomplete',
            'payment_mobile_not_received',
            'amount_incorrect',
            'wrong_receiver_data',
            'other'
        )
    );
