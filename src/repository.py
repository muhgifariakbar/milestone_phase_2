"""Participant task: identity-bound, read-only MongoDB queries."""


class Repository:
    def __init__(self, database):
        self.database = database

    def customer_for_token(self, token: str) -> dict | None:
        # TODO: Find identity by bearer token in demo_identities.
        # Never accept a client-supplied customer_id as authorization.
        raise NotImplementedError

    def assessment(self, customer_id: str) -> dict | None:
        # TODO: Query customer_assessments for this customer only. Verify model version,
        # 36-month mean, tier, limit, and reason evidence before using them.
        raise NotImplementedError

    def balance_summary(self, customer_id: str) -> dict | None:
        # TODO: Read only this customer's 36 monthly_balances rows and compute the mean.
        raise NotImplementedError
