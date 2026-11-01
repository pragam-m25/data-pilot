import asyncio
import pytest
from app.core.security import encrypt_secret, decrypt_secret, get_password_hash, verify_password, create_access_token, decode_access_token
from app.services.llm.factory import get_llm_adapter
from app.schemas.specs import DashboardSpec, PipelineSpec, AppProjectSpec, WorkflowSpec

def test_aes256_encryption():
    secret = "postgresql://user:p@ssw0rd!@db.internal:5432/production"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret

def test_password_hashing():
    pw = "SuperSecure123!"
    hashed = get_password_hash(pw)
    assert verify_password(pw, hashed)
    assert not verify_password("WrongPassword", hashed)

def test_jwt_token():
    user_id = "user-12345-uuid"
    token = create_access_token(user_id)
    decoded = decode_access_token(token)
    assert decoded == user_id

def test_llm_adapter_structured_specs():
    async def _run():
        adapter = get_llm_adapter("mock")
        
        # Test DashboardSpec generation
        dash = await adapter.complete_structured("Create sales and revenue metrics", DashboardSpec)
        assert isinstance(dash, DashboardSpec)
        assert len(dash.widgets) >= 3
        assert all(w.sql for w in dash.widgets)
        
        # Test PipelineSpec generation
        pipe = await adapter.complete_structured("Daily sync from Postgres to warehouse", PipelineSpec)
        assert isinstance(pipe, PipelineSpec)
        assert len(pipe.nodes) >= 3
        assert len(pipe.edges) >= 2
        
        # Test AppProjectSpec generation with Inspector tags
        app_proj = await adapter.complete_structured("SaaS billing portal", AppProjectSpec)
        assert isinstance(app_proj, AppProjectSpec)
        assert len(app_proj.components) >= 2
        assert all(c.dp_id for c in app_proj.components)
        
        # Test WorkflowSpec generation
        workflow = await adapter.complete_structured("Alert on churn increase", WorkflowSpec)
        assert isinstance(workflow, WorkflowSpec)
        assert any(n.type == "human_approval" for n in workflow.nodes)

    asyncio.run(_run())
