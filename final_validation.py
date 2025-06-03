"""
This script validates that our fix was properly applied to the research_flow.py file.
"""

import re

def validate_fix():
    file_path = "app/orchestration/research_flow.py"
    
    # Read the content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for key indicators that our fix was applied
    indicators = [
        "# Create system message with the system prompt",
        "system_message = {",
        "\"role\": \"system\"",
        "\"content\": base_system_prompt",
        "user_message = {",
        "\"role\": \"user\"",
        "messages = [system_message, user_message]",
        "response = await model_client.chat.completions.create(",
        "analysis = response.choices[0].message.content"
    ]
    
    missing_indicators = []
    for indicator in indicators:
        if indicator not in content:
            missing_indicators.append(indicator)
    
    if missing_indicators:
        print("❌ Fix validation FAILED!")
        print("The following expected code patterns were not found:")
        for missing in missing_indicators:
            print(f"  - {missing}")
        return False
    else:
        print("✅ Fix validation PASSED!")
        print("All expected code patterns were found in the file.")
        
        # Check that the old templated response code is gone
        old_patterns = [
            "response_parts = []",
            "response_parts.append(f\"# Research Analysis: {question}\")",
            "response_parts.append(\"## Web Research Findings\")",
            "response_parts.append(web_results)"
        ]
        
        found_old_patterns = []
        for pattern in old_patterns:
            if pattern in content:
                found_old_patterns.append(pattern)
        
        if found_old_patterns:
            print("\n⚠️ WARNING: Some old code patterns were still found:")
            for pattern in found_old_patterns:
                print(f"  - {pattern}")
            return False
        else:
            print("\n✅ All old templated response code was successfully removed.")
            return True

if __name__ == "__main__":
    print("Validating research_flow.py fix...")
    validate_fix() 