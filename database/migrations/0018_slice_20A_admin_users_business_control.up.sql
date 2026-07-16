create index if not exists users_phone_admin_search_idx
    on users (phone)
    where phone is not null and phone <> '';

create index if not exists users_username_lower_admin_search_idx
    on users (lower(username))
    where username is not null and username <> '';
