# R-11_RATING.md

SCREEN_ID: R-11_RATING
actor: remitter
slice: slice_42B_order_ratings
status: BUILD_APPROVED

purpose:
Rate the business with stars after an owned completed order without leaving the
chat-first flow.

route:
- compact action inside the completed order chat
- compatible action in owned order detail

entry points:
Owned completed order chat or detail

exit points:
The current chat/detail remains open after success or error.

data required:
- authenticated user/session
- owned order in `completed`
- backend rating eligibility

write strategy:
- Writes only through `POST /api/v1/orders/{id}/rating`.
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

presentation:
- compact system bubble: `Como fue esta orden?`
- 1..5 stars and compact `Calificar` action
- already rated copy: `Calificaste X de 5`
- no dedicated screen is required
- failed submit preserves the selected stars

audit events:
rating_created

QA checklist:
- no comments
- no duplicate rating
- ownership validated by backend
- no frontend reputation calculation
