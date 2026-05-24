from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.evaluator import evaluate_hypothesis
from app.models import Customer, Hypothesis, ProductRate, SignalSample, Tenant


def test_idle_shutdown_hypothesis_matches_seed_resource():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(Tenant(id="tenant-demo", name="Demo"))
    session.add(Customer(id="cust-acme", tenant_id="tenant-demo", name="Acme"))
    session.add(
        ProductRate(
            provider="AWS",
            resource_type="vm",
            sku="m6i.large",
            region="us-east-1",
            pricing_model="on_demand",
            unit="hour",
            rate=0.096,
            compatibility_group="compute.vm.same-architecture-family",
            snapshot_id="test",
        )
    )
    for signal, value in [
        ("compute.vm.cpu_utilisation_pct", 2.0),
        ("compute.vm.network_egress_mbps", 0.02),
        ("storage.volume.iops", 2.0),
    ]:
        session.add(
            SignalSample(
                tenant_id="tenant-demo",
                customer_id="cust-acme",
                provider="AWS",
                account_id="aws-prod",
                resource_id="i-idle",
                resource_type="vm",
                region="us-east-1",
                sku="m6i.large",
                signal_name=signal,
                value=value,
                unit="%",
            )
        )
    hypothesis = Hypothesis(
        tenant_id="tenant-demo",
        name="Idle VM",
        severity="P0",
        scope={"providers": ["AWS"]},
        conditions=[
            {"signal": "compute.vm.cpu_utilisation_pct", "operator": "<", "value": 5},
            {"signal": "compute.vm.network_egress_mbps", "operator": "<", "value": 0.1},
            {"signal": "storage.volume.iops", "operator": "<", "value": 5},
        ],
        action_proposal={"type": "Shutdown"},
    )
    session.add(hypothesis)
    session.commit()

    result = evaluate_hypothesis(session, hypothesis, days=30, persist=False)

    assert result["hit_count"] == 1
    assert result["estimated_savings_monthly"] > 0
