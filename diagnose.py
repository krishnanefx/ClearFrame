"""
Quick diagnostic test
"""
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("🔍 Diagnostic Test")
print("="*50)

# Check credentials
team_id = os.getenv('HOLISTIC_AI_TEAM_ID')
api_token = os.getenv('HOLISTIC_AI_API_TOKEN')
valyu_key = os.getenv('VALYU_API_KEY')

print(f"Team ID: {team_id}")
print(f"API Token: {'✅ Set' if api_token else '❌ Missing'}")
print(f"Valyu Key: {'✅ Set' if valyu_key else '❌ Missing'}")

# Test basic connectivity
import requests
try:
    # Test if we can reach the API endpoint
    url = f"https://api.holisticai.com/bedrock-proxy/teams/{team_id}/v1/models"
    headers = {"Authorization": f"Bearer {api_token}"}
    print(f"\n🌐 Testing API endpoint: {url}")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ API connection successful!")
    else:
        print(f"❌ API returned {response.status_code}")
except requests.exceptions.Timeout:
    print("❌ Connection timeout - API may be down")
except requests.exceptions.ConnectionError:
    print("❌ Connection error - check network/firewall")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n💡 Possible solutions:")
print("1. Check if team credentials are correct")
print("2. Verify internet connection")
print("3. Try using OpenAI instead (set OPENAI_API_KEY)")
print("4. Contact @zekunwu_73994 for new credentials")