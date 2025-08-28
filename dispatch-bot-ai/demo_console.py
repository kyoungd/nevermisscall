#!/usr/bin/env python3
"""
NOTE: Run this with the virtual environment activated:
    source venv/bin/activate
    python demo_console.py

Or use: PYTHONPATH=src ./venv/bin/python demo_console.py
"""
"""
Never Missed Call AI - Production Demo Console

This console application tests real customer interactions with the production AI system
using actual OpenAI GPT-4 and Google Maps APIs. You can type messages as a customer 
would, and see the complete API response with real AI intelligence.

REQUIREMENTS:
- OPENAI_API_KEY environment variable
- GOOGLE_MAPS_API_KEY environment variable

Usage: python demo_console.py
"""

import asyncio
import json
import random
import uuid
from datetime import datetime
from typing import Dict, Any

# Add src to Python path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dispatch_bot.models.basic_schemas import BasicDispatchRequest, BasicDispatchResponse, ConversationStage
from dispatch_bot.models.openai_models import ConversationContext
from dispatch_bot.services.conversational_ai_service import ConversationalAIService
from dispatch_bot.services.openai_service import OpenAIService
from dispatch_bot.services.geocoding_service import GeocodingService
from dispatch_bot.services.scheduling_engine import SchedulingEngine


class DemoConsole:
    """Interactive console for testing the Never Missed Call AI system"""
    
    def __init__(self):
        """Initialize the demo console with realistic business data"""
        self.conversation_id = str(uuid.uuid4()).replace('-', '')[:12]  # 12 chars, no dashes
        self.phone_number = self._generate_random_phone()
        self.business_data = self._generate_business_data()
        
        # Initialize conversational AI service
        self.conversational_ai = self._setup_conversational_ai()
        self.conversation_context = ConversationContext(
            conversation_id=self.conversation_id,
            customer_phone=self.phone_number,
            business_name=self.business_data["name"]
        )
        
        # Track conversation turns for display
        self.conversation_history = []
        
        print("🔧 Never Missed Call AI - Production Demo")  
        print("=" * 50)
        self._display_scenario()
    
    def _generate_random_phone(self) -> str:
        """Generate a random phone number"""
        area_code = random.choice([212, 213, 415, 310, 323, 818, 714, 949])
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        return f"+1{area_code}{exchange}{number}"
    
    def _generate_business_data(self) -> Dict[str, Any]:
        """Generate realistic business data using Chatsworth area addresses"""
        businesses = [
            {
                "name": "Chatsworth Plumbing Pro",
                "address": "9425 Penfield Avenue, Chatsworth, CA 91311",  # Near Courthouse
                "phone": "(555) 123-PLUMB",
                "service_radius": 25
            },
            {
                "name": "West Valley Plumbing Services",
                "address": "21052 Devonshire Street, Chatsworth, CA 91311",  # Near Library
                "phone": "(555) 987-PIPE",
                "service_radius": 30
            },
            {
                "name": "Emergency Plumbers Chatsworth",
                "address": "21606 Devonshire Street, Chatsworth, CA 91311",  # Near Post Office
                "phone": "(555) 456-HELP",
                "service_radius": 20
            }
        ]
        return random.choice(businesses)
    
    def _setup_conversational_ai(self) -> ConversationalAIService:
        """Setup conversational AI service with real production APIs"""
        import os
        
        # Check for required API keys
        openai_api_key = os.getenv('OPENAI_API_KEY')
        google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        if not openai_api_key:
            raise ValueError("""
❌ OPENAI_API_KEY environment variable is required for production testing.

Set it with:
    export OPENAI_API_KEY="your_openai_api_key_here"

Or create a .env file:
    echo "OPENAI_API_KEY=your_key_here" >> .env
            """)
            
        if not google_maps_api_key:
            raise ValueError("""
❌ GOOGLE_MAPS_API_KEY environment variable is required for production testing.

Set it with:
    export GOOGLE_MAPS_API_KEY="your_google_maps_api_key_here"

Or create a .env file:
    echo "GOOGLE_MAPS_API_KEY=your_key_here" >> .env
            """)
        
        # Create real production services
        print("🔌 Connecting to production APIs...")
        print(f"   ✅ OpenAI GPT-4 API (key: {openai_api_key[:8]}...)")
        print(f"   ✅ Google Maps API (key: {google_maps_api_key[:8]}...)")
        
        real_openai = OpenAIService(api_key=openai_api_key)
        real_geocoding = GeocodingService(api_key=google_maps_api_key)
        
        # Use real scheduling engine with afternoon-only availability (per real_addresses.md)
        realistic_scheduling = SchedulingEngine(
            business_hours_start="13:00",  # 1 PM start (mornings taken per real_addresses.md)
            business_hours_end="19:00",    # 7 PM end 
            slot_duration_hours=2,         # 2-hour appointments
            advance_booking_days=7         # Book up to week ahead
        )
        
        return ConversationalAIService(
            openai_service=real_openai,
            geocoding_service=real_geocoding,
            scheduling_engine=realistic_scheduling
        )
    
    def _display_scenario(self):
        """Display the current demo scenario"""
        print(f"📞 Scenario: Customer calling {self.business_data['name']}")
        print(f"🏢 Business: {self.business_data['address']}")
        print(f"📱 Your phone: {self.phone_number}")
        print(f"🆔 Conversation ID: {self.conversation_id} ({len(self.conversation_id)} chars)")
        print(f"🌐 Service area: {self.business_data['service_radius']} mile radius")
        print("📅 Schedule: Mornings booked (8AM-1PM), afternoons available")
        print("🤖 Using REAL OpenAI GPT-4 and Google Maps APIs")
        print()
        print("💡 Try messages like:")
        print("   • My kitchen faucet is leaking at 10027 Lurline Avenue, Chatsworth, CA 91311")
        print("   • Toilet won't flush, I'm at 10100 Variel Avenue, Chatsworth CA")
        print("   • Emergency! Pipe burst flooding basement, 22005 Devonshire Street, Chatsworth")
        print("   • Need drain cleaning at 21050 Plummer Street, Chatsworth CA 91311")
        print()
        print("Type 'quit' to exit, 'reset' to start new conversation")
        print("-" * 50)
    
    async def run(self):
        """Run the interactive console loop"""
        while True:
            try:
                # Get user input
                print(f"\n💬 Customer Message (Conversation {len(self.conversation_history)//2 + 1}):")
                user_input = input("You: ").strip()
                
                if user_input.lower() == 'quit':
                    print("\n👋 Thanks for testing Never Missed Call AI!")
                    break
                
                if user_input.lower() == 'reset':
                    self._reset_conversation()
                    continue
                
                if not user_input:
                    print("❌ Please enter a message")
                    continue
                
                # Process the message
                print("\n⚙️  Processing your message...")
                await self._process_message(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Thanks for testing Never Missed Call AI!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("Please try again or type 'reset' to start over.")
    
    async def _process_message(self, message: str):
        """Process a customer message through the conversational AI system"""
        try:
            # Create business info context
            business_info = {
                "name": self.business_data["name"],
                "address": self.business_data["address"],
                "phone": self.business_data["phone"],
                "service_radius": self.business_data["service_radius"]
            }
            
            # Let the conversational AI handle everything
            ai_result = await self.conversational_ai.handle_conversation_turn(
                customer_message=message,
                conversation_context=self.conversation_context,
                business_info=business_info
            )
            
            # Track conversation history
            self.conversation_history.append(message)
            self.conversation_history.append(ai_result.get("ai_response", ""))
            
            # Display the results
            self._display_conversational_response(message, ai_result)
            
        except Exception as e:
            print(f"❌ AI Error: {str(e)}")
            if "validation error" in str(e).lower():
                print("💡 This is usually a data validation issue. Try 'reset' to start fresh.")
            else:
                print("💡 This might happen if services aren't fully configured.")
            print("📞 In a real system, this would escalate to human support.")
    
    def _display_response(self, user_message: str, response: BasicDispatchResponse):
        """Display the AI response in a formatted way"""
        print("\n" + "=" * 60)
        print("🤖 Never Missed Call AI Response")
        print("=" * 60)
        
        # Show what the AI understood
        print("\n📋 What I understood:")
        if response.job_type:
            print(f"   🔧 Job Type: {response.job_type.replace('_', ' ').title()}")
        if response.customer_address:
            print(f"   📍 Address: {response.customer_address}")
            print(f"   ✅ Valid Address: {response.address_valid}")
            print(f"   🌐 In Service Area: {response.in_service_area}")
        if hasattr(response, 'urgency_level'):
            print(f"   ⚡ Urgency: {response.urgency_level.title()}")
        
        # Show appointment details if offered
        if response.appointment_offered:
            print("\n📅 Appointment Offered:")
            if response.proposed_start_time:
                print(f"   📆 Date: {response.proposed_start_time.strftime('%A, %B %d, %Y')}")
                print(f"   🕒 Time: {response.proposed_start_time.strftime('%I:%M %p')} - {response.proposed_end_time.strftime('%I:%M %p')}")
            if response.estimated_price_min and response.estimated_price_max:
                print(f"   💰 Estimated Cost: ${response.estimated_price_min:.0f} - ${response.estimated_price_max:.0f}")
        
        # Show conversation status
        print(f"\n📞 Conversation Status: {response.conversation_stage.value.replace('_', ' ').title()}")
        if response.requires_followup:
            print(f"   ⏰ Timeout: {response.conversation_timeout_minutes} minutes")
        
        # Show the AI's message to customer
        print("\n💬 AI Response to Customer:")
        print(f"   \"{response.next_message}\"")
        
        # Show next steps
        print(f"\n🎯 Next Steps:")
        if response.conversation_stage == ConversationStage.COLLECTING_INFO:
            print("   → AI needs more information from customer")
        elif response.conversation_stage == ConversationStage.CONFIRMING:
            print("   → Customer should respond with YES or NO")
        elif response.conversation_stage == ConversationStage.COMPLETE:
            print("   → Conversation complete")
        else:
            print(f"   → Continue conversation ({response.conversation_stage.value})")
        
        print("\n" + "-" * 60)
    
    def _display_conversational_response(self, user_message: str, ai_result: Dict[str, Any]):
        """Display the conversational AI response"""
        print("\n" + "=" * 60)
        print("🤖 Never Missed Call AI - Conversational Response")
        print("=" * 60)
        
        # Show the main AI response
        print("\n💬 AI Response:")
        print(f'   "{ai_result["ai_response"]}"')
        
        # Show AI's understanding/assessment
        assessment = ai_result.get("ai_assessment", {})
        if assessment:
            print("\n🧠 AI Assessment:")
            if assessment.get("job_type"):
                print(f"   🔧 Job Type: {assessment['job_type'].replace('_', ' ').title()}")
            if assessment.get("address"):
                print(f"   📍 Address: {assessment['address']}")
            if assessment.get("urgency"):
                print(f"   ⚡ Urgency: {assessment['urgency'].title()}")
            if assessment.get("ready_to_schedule"):
                print(f"   📅 Ready to Schedule: {'✅ Yes' if assessment['ready_to_schedule'] else '❌ No'}")
        
        # Show conversation stage
        stage = ai_result.get("conversation_stage", "continuing")
        stage_display = stage.replace('_', ' ').title()
        print(f"\n📞 Conversation Stage: {stage_display}")
        
        # Show business actions taken
        actions = ai_result.get("actions_taken", [])
        if actions:
            print(f"\n⚙️  Business Actions Taken:")
            for action in actions:
                print(f"   • {action.replace('_', ' ').title()}")
        
        # Show AI's next steps
        next_steps = ai_result.get("next_steps", [])
        if next_steps:
            print(f"\n🎯 AI's Next Steps:")
            for step in next_steps:
                print(f"   → {step}")
        
        print("\n" + "-" * 60)
    
    def _reset_conversation(self):
        """Reset to start a new conversation"""
        self.conversation_id = str(uuid.uuid4()).replace('-', '')[:12]  # 12 chars, no dashes
        self.phone_number = self._generate_random_phone()
        self.business_data = self._generate_business_data()
        
        # Reset conversation context
        self.conversation_context = ConversationContext(
            conversation_id=self.conversation_id,
            customer_phone=self.phone_number,
            business_name=self.business_data["name"]
        )
        
        # Reset conversation history
        self.conversation_history = []
        
        print("\n🔄 Starting new conversation...")
        self._display_scenario()


# Production services - no mocking


async def main():
    """Main entry point for the demo console"""
    print("🚀 Starting Never Missed Call AI Demo Console...")
    print("🔌 This demo uses REAL OpenAI GPT-4 and Google Maps APIs")
    
    try:
        # Initialize and run the demo
        demo = DemoConsole()
        await demo.run()
    except ValueError as e:
        print(str(e))
        print("\n💡 Set your API keys and try again!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if we're in the right directory
    if not os.path.exists("src/dispatch_bot"):
        print("❌ Error: Please run this script from the project root directory.")
        print("   cd /home/young/Desktop/Code/nvermisscall/nmc-ai")
        print("   python demo_console.py")
        sys.exit(1)
    
    # Run the async main function
    asyncio.run(main())
