#!/usr/bin/env python3
"""
Comprehensive Test Script for Conversation History & System Prompt Features

This script tests the new conversation and system prompt capabilities
of the PharmaDB Research Microservice.
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Test configuration
BASE_URL = "https://pharmadb-research-agent-v1.onrender.com"  # Update with your deployed URL
TIMEOUT = 300  # 5 minutes

class ConversationFeaturesTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    async def test_endpoint(self, payload: dict) -> dict:
        """Test the research endpoint with custom payload"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/research",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
    
    async def test_simple_conversation_history(self) -> Dict[str, Any]:
        """Test conversation history functionality"""
        print("🧪 Testing Conversation History...")
        
        try:
            # Step 1: First question to establish context
            first_payload = {
                "question": "What are the main classes of diabetes medications?"
            }
            
            print("  → Asking initial question about diabetes medications")
            first_response = await self.test_endpoint(first_payload)
            
            if not first_response.get("success"):
                return {"status": "❌ FAIL", "error": "First question failed"}
            
            # Step 2: Follow-up question with conversation history
            conversation_history = [
                {
                    "role": "user",
                    "content": "What are the main classes of diabetes medications?",
                    "timestamp": datetime.now().isoformat(),
                    "source": "user"
                },
                {
                    "role": "assistant",
                    "content": first_response["final_answer"][:300] + "...",  # Truncate for test
                    "timestamp": datetime.now().isoformat(),
                    "source": "assistant"
                }
            ]
            
            second_payload = {
                "question": "What about dosing considerations for elderly patients?",
                "conversation_history": conversation_history
            }
            
            print("  → Asking follow-up question with conversation history")
            second_response = await self.test_endpoint(second_payload)
            
            if not second_response.get("success"):
                return {"status": "❌ FAIL", "error": "Follow-up question failed"}
            
            # Check if conversation context was processed
            agent_steps = second_response.get("agent_steps", [])
            context_processed = any("conversation history" in step.get("content", "").lower() 
                                 for step in agent_steps)
            
            # Check if response acknowledges context
            final_answer = second_response["final_answer"].lower()
            context_acknowledged = any(term in final_answer for term in [
                "previous", "our discussion", "continuing", "earlier", "context"
            ])
            
            return {
                "status": "✅ PASS" if context_processed else "⚠️ PARTIAL",
                "context_processed": context_processed,
                "context_acknowledged": context_acknowledged,
                "processing_time": second_response.get("processing_time_seconds", 0),
                "agent_steps": len(agent_steps),
                "notes": f"Context processing: {'Yes' if context_processed else 'No'}, "
                        f"Acknowledgment: {'Yes' if context_acknowledged else 'No'}"
            }
            
        except Exception as e:
            return {"status": "❌ FAIL", "error": str(e)}
    
    async def test_system_prompt_regulatory(self) -> Dict[str, Any]:
        """Test regulatory affairs system prompt"""
        print("🧪 Testing System Prompt (Regulatory Specialist)...")
        
        try:
            regulatory_prompt = """You are a senior regulatory affairs specialist with 15 years of FDA experience. 
Focus on regulatory compliance, safety data interpretation, submission requirements, and potential FDA concerns. 
Provide specific guidance on documentation needs for drug approvals."""
            
            payload = {
                "question": "What are the key requirements for FDA drug approval?",
                "system_prompt": regulatory_prompt
            }
            
            print("  → Testing regulatory specialist expertise")
            response = await self.test_endpoint(payload)
            
            if not response.get("success"):
                return {"status": "❌ FAIL", "error": "Regulatory system prompt test failed"}
            
            # Check if response reflects regulatory perspective
            final_answer = response["final_answer"].lower()
            regulatory_terms = ["fda", "regulatory", "compliance", "submission", "approval", 
                              "safety", "documentation", "clinical trial", "phase"]
            
            regulatory_focus = sum(1 for term in regulatory_terms if term in final_answer)
            
            # Check agent steps for system prompt usage
            agent_steps = response.get("agent_steps", [])
            system_prompt_used = any("specialized expertise" in step.get("content", "") 
                                   for step in agent_steps)
            
            return {
                "status": "✅ PASS" if regulatory_focus >= 3 else "⚠️ PARTIAL",
                "regulatory_terms_found": regulatory_focus,
                "total_regulatory_terms": len(regulatory_terms),
                "system_prompt_detected": system_prompt_used,
                "processing_time": response.get("processing_time_seconds", 0),
                "notes": f"Found {regulatory_focus}/{len(regulatory_terms)} regulatory terms"
            }
            
        except Exception as e:
            return {"status": "❌ FAIL", "error": str(e)}
    
    async def test_system_prompt_clinical(self) -> Dict[str, Any]:
        """Test clinical pharmacologist system prompt"""
        print("🧪 Testing System Prompt (Clinical Pharmacologist)...")
        
        try:
            clinical_prompt = """You are a clinical pharmacologist specializing in diabetes care. 
Focus on mechanism of action, efficacy data, safety profiles, drug interactions, 
and patient selection criteria. Provide evidence-based clinical guidance."""
            
            payload = {
                "question": "Compare the efficacy of metformin vs sulfonylureas for diabetes",
                "system_prompt": clinical_prompt
            }
            
            print("  → Testing clinical pharmacologist expertise")
            response = await self.test_endpoint(payload)
            
            if not response.get("success"):
                return {"status": "❌ FAIL", "error": "Clinical system prompt test failed"}
            
            # Check if response reflects clinical perspective
            final_answer = response["final_answer"].lower()
            clinical_terms = ["efficacy", "mechanism", "action", "safety", "clinical", 
                            "patient", "drug", "interaction", "dosing", "therapeutic"]
            
            clinical_focus = sum(1 for term in clinical_terms if term in final_answer)
            
            return {
                "status": "✅ PASS" if clinical_focus >= 3 else "⚠️ PARTIAL",
                "clinical_terms_found": clinical_focus,
                "total_clinical_terms": len(clinical_terms),
                "processing_time": response.get("processing_time_seconds", 0),
                "notes": f"Found {clinical_focus}/{len(clinical_terms)} clinical terms"
            }
            
        except Exception as e:
            return {"status": "❌ FAIL", "error": str(e)}
    
    async def test_combined_features(self) -> Dict[str, Any]:
        """Test conversation history + system prompt together"""
        print("🧪 Testing Combined Features (History + System Prompt)...")
        
        try:
            # Step 1: Initial question with clinical system prompt
            clinical_prompt = """You are a geriatric pharmacologist specializing in elderly patient care. 
Focus on age-related pharmacokinetic changes, drug interactions, and safety considerations for older adults."""
            
            first_payload = {
                "question": "What are the safety considerations for diabetes medications in elderly patients?",
                "system_prompt": clinical_prompt
            }
            
            print("  → Initial question with geriatric specialist prompt")
            first_response = await self.test_endpoint(first_payload)
            
            if not first_response.get("success"):
                return {"status": "❌ FAIL", "error": "Initial combined test failed"}
            
            # Step 2: Follow-up with conversation history + different system prompt
            conversation_history = [
                {
                    "role": "user",
                    "content": "What are the safety considerations for diabetes medications in elderly patients?",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "role": "assistant",
                    "content": first_response["final_answer"][:200] + "...",
                    "timestamp": datetime.now().isoformat()
                }
            ]
            
            regulatory_prompt = """You are a regulatory affairs specialist. 
Focus on FDA guidelines, labeling requirements, and regulatory safety data for elderly populations."""
            
            second_payload = {
                "question": "What FDA guidelines apply to these safety considerations?",
                "conversation_history": conversation_history,
                "system_prompt": regulatory_prompt
            }
            
            print("  → Follow-up question with conversation history + regulatory prompt")
            second_response = await self.test_endpoint(second_payload)
            
            if not second_response.get("success"):
                return {"status": "❌ FAIL", "error": "Follow-up combined test failed"}
            
            # Analyze if both features worked
            agent_steps = second_response.get("agent_steps", [])
            history_processed = any("conversation history" in step.get("content", "").lower() 
                                  for step in agent_steps)
            prompt_used = any("specialized expertise" in step.get("content", "") 
                            for step in agent_steps)
            
            final_answer = second_response["final_answer"].lower()
            regulatory_terms = ["fda", "regulatory", "guideline", "labeling"]
            context_terms = ["previous", "earlier", "discussion", "safety considerations"]
            
            regulatory_focus = sum(1 for term in regulatory_terms if term in final_answer)
            context_awareness = sum(1 for term in context_terms if term in final_answer)
            
            return {
                "status": "✅ PASS" if (history_processed and prompt_used) else "⚠️ PARTIAL",
                "history_processed": history_processed,
                "system_prompt_used": prompt_used,
                "regulatory_focus": regulatory_focus,
                "context_awareness": context_awareness,
                "processing_time": second_response.get("processing_time_seconds", 0),
                "notes": f"History: {'✓' if history_processed else '✗'}, "
                        f"Prompt: {'✓' if prompt_used else '✗'}, "
                        f"Regulatory: {regulatory_focus}, Context: {context_awareness}"
            }
            
        except Exception as e:
            return {"status": "❌ FAIL", "error": str(e)}

async def run_comprehensive_tests(base_url: str) -> Dict[str, Any]:
    """Run all conversation feature tests"""
    
    print("🚀 Starting Comprehensive Conversation Features Test Suite")
    print("=" * 70)
    print(f"Testing API at: {base_url}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    tester = ConversationFeaturesTester(base_url)
    results = {
        "base_url": base_url,
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # Test 1: Conversation History
    print("=" * 50)
    result1 = await tester.test_simple_conversation_history()
    results["tests"]["conversation_history"] = result1
    print(f"Result: {result1['status']}")
    if "notes" in result1:
        print(f"Notes: {result1['notes']}")
    print()
    
    # Test 2: System Prompt (Regulatory)
    print("=" * 50)
    result2 = await tester.test_system_prompt_regulatory()
    results["tests"]["system_prompt_regulatory"] = result2
    print(f"Result: {result2['status']}")
    if "notes" in result2:
        print(f"Notes: {result2['notes']}")
    print()
    
    # Test 3: System Prompt (Clinical)
    print("=" * 50)
    result3 = await tester.test_system_prompt_clinical()
    results["tests"]["system_prompt_clinical"] = result3
    print(f"Result: {result3['status']}")
    if "notes" in result3:
        print(f"Notes: {result3['notes']}")
    print()
    
    # Test 4: Combined Features
    print("=" * 50)
    result4 = await tester.test_combined_features()
    results["tests"]["combined_features"] = result4
    print(f"Result: {result4['status']}")
    if "notes" in result4:
        print(f"Notes: {result4['notes']}")
    print()
    
    # Summary
    print("=" * 70)
    print("📊 CONVERSATION FEATURES TEST SUMMARY")
    print("=" * 70)
    
    passed_tests = sum(1 for test in results["tests"].values() 
                      if test["status"].startswith("✅"))
    partial_tests = sum(1 for test in results["tests"].values() 
                       if test["status"].startswith("⚠️"))
    total_tests = len(results["tests"])
    
    print(f"✅ Passed: {passed_tests}")
    print(f"⚠️  Partial: {partial_tests}")
    print(f"❌ Failed: {total_tests - passed_tests - partial_tests}")
    print(f"📈 Total: {total_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL CONVERSATION FEATURES WORKING PERFECTLY!")
        results["overall_status"] = "✅ FULLY FUNCTIONAL"
    elif passed_tests + partial_tests == total_tests:
        print("\n✅ CONVERSATION FEATURES ARE FUNCTIONAL!")
        print("Some features may need fine-tuning but core functionality works.")
        results["overall_status"] = "✅ FUNCTIONAL"
    else:
        print("\n⚠️ SOME CONVERSATION FEATURES NEED ATTENTION")
        results["overall_status"] = "⚠️ NEEDS ATTENTION"
    
    print(f"\nAverage processing time: {sum(t.get('processing_time', 0) for t in results['tests'].values()) / total_tests:.2f}s")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test conversation history & system prompt features")
    parser.add_argument("--url", default=BASE_URL, help="Base URL of the API")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    async def main():
        results = await run_comprehensive_tests(args.url)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Results saved to: {args.output}")
    
    asyncio.run(main()) 