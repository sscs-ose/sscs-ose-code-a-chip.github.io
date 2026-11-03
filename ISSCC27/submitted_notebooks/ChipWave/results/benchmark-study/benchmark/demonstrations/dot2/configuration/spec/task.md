# dot2

Implement benchmark_dot, a 2-lane signed INT8 dot product with a signed 32-bit sum.
Lane i uses packed bits [8*i +: 8] of req_a/req_b. Each product and the complete
sum are exact; sign-extend the result. Accept only when req_valid && req_ready.
Single outstanding request; req_ready stays low while busy. A request accepted
at edge t produces rsp_valid immediately after edge t+2 (three rising edges
counting the accepting edge). Hold rsp_valid/rsp_data until response handshake.
req_ready is high again AFTER a response-accepting edge; no same-edge bypass.
Active-low asynchronous reset or synchronous kill clears the outstanding work,
rsp_data=0, and returns to idle; kill immediately masks req_ready/rsp_valid.
No response from cancelled work. Inputs may change while busy. Mask ready/valid
while reset is low; rsp_data starts/reset-clears to zero and otherwise holds.

Use the fixed top-level port names and widths in interface.json. Develop with
`python3 tools/check.py`. Deliver synthesizable RTL under rtl/. Independent
final vectors/reference and scoring are outside your workspace. Do not alter
the task/checker, invoke extra models, or read other trials. The task's area
limit is installed after reference physical calibration, before evaluation.
