"""Integration tests for API endpoints."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from src.as_call_service.main import app


class TestAPIEndpoints:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return AsyncClient(app=app, base_url="http://test")

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test health endpoint."""
        with patch('src.as_call_service.controllers.health_controller.health_check', return_value=True):
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "services" in data

    @pytest.mark.asyncio
    async def test_health_endpoint_unhealthy(self, client):
        """Test health endpoint when unhealthy."""
        with patch('src.as_call_service.controllers.health_controller.health_check', return_value=False):
            response = await client.get("/health")
            
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "as-call-service"
        assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_service_info_endpoint(self, client):
        """Test service info endpoint."""
        response = await client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "as-call-service"
        assert "features" in data
        assert "limits" in data

    @pytest.mark.asyncio
    async def test_incoming_call_endpoint_success(self, client):
        """Test successful incoming call processing."""
        webhook_data = {
            "callSid": "CA1234567890abcdef",
            "from": "+12125551234",
            "to": "+13105551234",
            "tenantId": str(uuid4()),
            "callStatus": "ringing",
            "direction": "inbound",
        }

        mock_call = {
            "id": str(uuid4()),
            "callSid": webhook_data["callSid"],
            "status": "ringing",
            "tenantId": webhook_data["tenantId"],
            "customerPhone": webhook_data["from"],
            "businessPhone": webhook_data["to"],
        }

        with patch('src.as_call_service.services.call_service.call_service.process_incoming_call') as mock_process:
            mock_call_obj = type('MockCall', (), mock_call)()
            mock_process.return_value = mock_call_obj

            response = await client.post(
                "/calls/incoming",
                json=webhook_data,
                headers={"x-service-key": "nmc-internal-services-auth-key-phase1"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["call"]["callSid"] == webhook_data["callSid"]

    @pytest.mark.asyncio
    async def test_incoming_call_endpoint_unauthorized(self, client):
        """Test incoming call endpoint without proper authentication."""
        webhook_data = {
            "callSid": "CA1234567890abcdef",
            "from": "+12125551234",
            "to": "+13105551234",
        }

        response = await client.post("/calls/incoming", json=webhook_data)
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missed_call_endpoint_success(self, client):
        """Test successful missed call processing."""
        missed_call_data = {
            "callSid": "CA1234567890abcdef",
            "callStatus": "no-answer",
            "callDuration": 0,
            "endTime": datetime.utcnow().isoformat(),
        }

        mock_call = type('MockCall', (), {
            'id': uuid4(),
            'status': 'missed',
            'sms_triggered': True,
            'conversation_id': uuid4(),
        })()

        with patch('src.as_call_service.services.call_service.call_service.process_missed_call') as mock_process:
            mock_process.return_value = mock_call

            response = await client.post(
                "/calls/missed",
                json=missed_call_data,
                headers={"x-service-key": "nmc-internal-services-auth-key-phase1"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["call"]["smsTriggered"] is True

    @pytest.mark.asyncio
    async def test_get_call_endpoint_success(self, client):
        """Test successful get call endpoint."""
        call_id = uuid4()
        tenant_id = uuid4()
        
        mock_call = type('MockCall', (), {
            'id': call_id,
            'call_sid': 'CA1234567890abcdef',
            'tenant_id': tenant_id,
            'customer_phone': '+12125551234',
            'business_phone': '+13105551234',
            'direction': 'inbound',
            'status': 'completed',
            'start_time': datetime.utcnow(),
            'end_time': datetime.utcnow(),
            'duration': 45,
            'conversation_id': None,
            'lead_created': True,
        })()

        # Mock JWT verification
        mock_user_data = {
            'user_id': uuid4(),
            'tenant_id': tenant_id,
            'email': 'test@example.com',
            'role': 'admin',
        }

        with patch('src.as_call_service.services.call_service.call_service.get_call') as mock_get:
            mock_get.return_value = mock_call

            with patch('src.as_call_service.utils.auth.verify_jwt_token') as mock_verify:
                mock_verify.return_value = mock_user_data

                response = await client.get(
                    f"/calls/{call_id}",
                    headers={"Authorization": "Bearer valid-jwt-token"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["call"]["id"] == str(call_id)

    @pytest.mark.asyncio
    async def test_get_call_endpoint_forbidden(self, client):
        """Test get call endpoint with wrong tenant access."""
        call_id = uuid4()
        call_tenant_id = uuid4()
        user_tenant_id = uuid4()  # Different tenant
        
        mock_call = type('MockCall', (), {
            'tenant_id': call_tenant_id,
        })()

        mock_user_data = {
            'user_id': uuid4(),
            'tenant_id': user_tenant_id,  # Different from call tenant
        }

        with patch('src.as_call_service.services.call_service.call_service.get_call') as mock_get:
            mock_get.return_value = mock_call

            with patch('src.as_call_service.utils.auth.verify_jwt_token') as mock_verify:
                mock_verify.return_value = mock_user_data

                response = await client.get(
                    f"/calls/{call_id}",
                    headers={"Authorization": "Bearer valid-jwt-token"}
                )

                assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_process_incoming_message_success(self, client):
        """Test successful incoming message processing."""
        conversation_id = uuid4()
        message_data = {
            "messageSid": "SM1234567890abcdef",
            "body": "I need help with my plumbing",
        }

        mock_result = {
            "id": str(uuid4()),
            "conversationId": str(conversation_id),
            "direction": "inbound",
            "processed": True,
            "aiProcessingTriggered": False,
            "humanResponseWindow": 60,
        }

        with patch('src.as_call_service.services.conversation_service.conversation_service.process_incoming_message') as mock_process:
            mock_process.return_value = mock_result

            response = await client.post(
                f"/conversations/{conversation_id}/messages",
                json=message_data,
                headers={"x-service-key": "nmc-internal-services-auth-key-phase1"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["aiProcessingTriggered"] is False

    @pytest.mark.asyncio
    async def test_send_human_reply_success(self, client):
        """Test successful human reply sending."""
        conversation_id = uuid4()
        tenant_id = uuid4()
        
        reply_data = {
            "message": "I can help with that! When would be good for you?",
            "takeOverFromAI": True
        }

        mock_conversation = type('MockConversation', (), {
            'tenant_id': tenant_id,
        })()

        mock_result = {
            "id": str(uuid4()),
            "conversationId": str(conversation_id),
            "direction": "outbound",
            "sender": "human",
            "aiDeactivated": True,
        }

        mock_user_data = {
            'user_id': uuid4(),
            'tenant_id': tenant_id,
        }

        with patch('src.as_call_service.services.conversation_service.conversation_service.get_conversation') as mock_get_conv:
            mock_get_conv.return_value = mock_conversation

            with patch('src.as_call_service.services.conversation_service.conversation_service.send_human_reply') as mock_reply:
                mock_reply.return_value = mock_result

                with patch('src.as_call_service.utils.auth.verify_jwt_token') as mock_verify:
                    mock_verify.return_value = mock_user_data

                    response = await client.post(
                        f"/conversations/{conversation_id}/reply",
                        json=reply_data,
                        headers={"Authorization": "Bearer valid-jwt-token"}
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["aiDeactivated"] is True

    @pytest.mark.asyncio
    async def test_get_conversation_success(self, client):
        """Test successful get conversation endpoint."""
        conversation_id = uuid4()
        tenant_id = uuid4()

        mock_conversation = type('MockConversation', (), {
            'id': conversation_id,
            'tenant_id': tenant_id,
            'customer_phone': '+12125551234',
            'business_phone': '+13105551234',
            'status': 'active',
            'ai_active': False,
            'human_takeover_time': None,
            'last_message_time': datetime.utcnow(),
            'message_count': 3,
            'lead_id': None,
            'created_at': datetime.utcnow(),
        })()

        mock_messages = [
            type('MockMessage', (), {
                'id': uuid4(),
                'direction': 'outbound',
                'body': 'Hi! Sorry we missed your call.',
                'sender': 'system',
                'sent_at': datetime.utcnow(),
            })(),
        ]

        mock_user_data = {
            'user_id': uuid4(),
            'tenant_id': tenant_id,
        }

        with patch('src.as_call_service.services.conversation_service.conversation_service.get_conversation') as mock_get_conv:
            mock_get_conv.return_value = mock_conversation

            with patch('src.as_call_service.services.conversation_service.conversation_service.get_conversation_messages') as mock_get_msgs:
                mock_get_msgs.return_value = mock_messages

                with patch('src.as_call_service.utils.auth.verify_jwt_token') as mock_verify:
                    mock_verify.return_value = mock_user_data

                    response = await client.get(
                        f"/conversations/{conversation_id}",
                        headers={"Authorization": "Bearer valid-jwt-token"}
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["conversation"]["id"] == str(conversation_id)
                    assert len(data["data"]["messages"]) == 1

    @pytest.mark.asyncio
    async def test_get_lead_success(self, client):
        """Test successful get lead endpoint."""
        lead_id = uuid4()
        tenant_id = uuid4()

        mock_lead = type('MockLead', (), {
            'id': lead_id,
            'tenant_id': tenant_id,
            'conversation_id': uuid4(),
            'customer_phone': '+12125551234',
            'customer_name': None,
            'customer_address': '123 Main St',
            'problem_description': 'Leaky faucet',
            'urgency_level': 'normal',
            'job_type': 'faucet_repair',
            'estimated_value': 200.0,
            'status': 'qualified',
            'ai_analysis': None,
            'created_at': datetime.utcnow(),
        })()

        mock_user_data = {
            'user_id': uuid4(),
            'tenant_id': tenant_id,
        }

        with patch('src.as_call_service.services.lead_service.lead_service.get_lead') as mock_get:
            mock_get.return_value = mock_lead

            with patch('src.as_call_service.utils.auth.verify_jwt_token') as mock_verify:
                mock_verify.return_value = mock_user_data

                response = await client.get(
                    f"/leads/{lead_id}",
                    headers={"Authorization": "Bearer valid-jwt-token"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["lead"]["id"] == str(lead_id)
                assert data["data"]["lead"]["problemDescription"] == "Leaky faucet"

    @pytest.mark.asyncio
    async def test_update_lead_status_success(self, client):
        """Test successful lead status update."""
        lead_id = uuid4()
        tenant_id = uuid4()

        status_update = {
            "status": "appointment_scheduled",
            "notes": "Scheduled for tomorrow 10 AM",
            "estimatedValue": 275.0
        }

        mock_lead = type('MockLead', (), {
            'tenant_id': tenant_id,
        })()

        mock_updated_lead = type('MockLead', (), {
            'id': lead_id,
            'status': 'appointment_scheduled',
            'status_notes': 'Scheduled for tomorrow 10 AM',
            'estimated_value': 275.0,
            'updated_at': datetime.utcnow(),
        })()

        mock_user_data = {
            'user_id': uuid4(),
            'tenant_id': tenant_id,
        }

        with patch('src.as_call_service.services.lead_service.lead_service.get_lead') as mock_get:
            mock_get.return_value = mock_lead

            with patch('src.as_call_service.services.lead_service.lead_service.update_lead_status') as mock_update:
                mock_update.return_value = mock_updated_lead

                with patch('src.as_call_service.utils.auth.verify_jwt_token') as mock_verify:
                    mock_verify.return_value = mock_user_data

                    response = await client.put(
                        f"/leads/{lead_id}/status",
                        json=status_update,
                        headers={"Authorization": "Bearer valid-jwt-token"}
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["lead"]["status"] == "appointment_scheduled"