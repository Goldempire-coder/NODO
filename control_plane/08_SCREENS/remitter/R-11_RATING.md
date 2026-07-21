# R-11_RATING.md

SCREEN_ID: R-11_RATING
actor: remitter
slice: future_business_reputation_rating_write
status: CONTRACT_ONLY_NOT_BUILT

purpose:
Rate the business with stars after an owned completed order.

route:
/orders/:id/rating

entry points:
Confirm received

exit points:
R-02_HOME_SEARCH

data required:
- authenticated user/session
- owned order in `completed`
- backend rating eligibility

write strategy:
- Writes only through a future approved API endpoint.
- One rating per completed order.
- Stars integer 1..5.
- No comment, review title or free text in MVP.
- Frontend never calculates aggregate reputation.

MainButton behavior:
Enviar calificacion

validation:
- stars required
- no textual review field

permissions:
own completed order

states:
- loading
- eligible
- already_rated
- error
- success

audit events:
rating_created (future write slice)

QA checklist:
- no comments
- no duplicate rating
- ownership validated by backend
- no rating UI is built in Slice 42A
