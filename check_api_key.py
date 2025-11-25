"""
Script to check API key access and permissions
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.models.service import Service
from app.core.security import hash_api_key, decrypt_api_key

async def check_api_key(api_key_str: str):
    """Check API key details and access"""
    async for db in get_db():
        try:
            # Hash the API key
            key_hash = hash_api_key(api_key_str)
            
            # Find the API key
            result = await db.execute(
                select(ApiKey).where(ApiKey.key_hash == key_hash)
            )
            api_key = result.scalar_one_or_none()
            
            if not api_key:
                print(f"❌ API Key not found: {api_key_str}")
                return
            
            # Get user
            user_result = await db.execute(
                select(User).where(User.id == api_key.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            print(f"✅ API Key Found!")
            print(f"   Key ID: {api_key.id}")
            print(f"   Key Name: {api_key.name}")
            print(f"   Key Prefix: {api_key.key_prefix}")
            print(f"   Status: {api_key.status.value}")
            print(f"   User: {user.email if user else 'N/A'} ({user.full_name if user else 'N/A'})")
            print(f"   User ID: {api_key.user_id}")
            print(f"   Allowed Services: {api_key.allowed_services}")
            print(f"   Service ID: {api_key.service_id}")
            print(f"   Has All Services Access: {'*' in (api_key.allowed_services or [])}")
            
            # Check GST service access
            gst_result = await db.execute(
                select(Service).where(Service.slug == "gst-verification")
            )
            gst_service = gst_result.scalar_one_or_none()
            
            if gst_service:
                print(f"\n📋 GST Service Details:")
                print(f"   Service ID: {gst_service.id}")
                print(f"   Service Name: {gst_service.name}")
                print(f"   Service Slug: {gst_service.slug}")
                print(f"   Is Active: {gst_service.is_active}")
                
                # Check access
                has_access = False
                if api_key.allowed_services:
                    if "*" in api_key.allowed_services:
                        has_access = True
                        print(f"\n✅ Access: Has ALL services access (wildcard)")
                    elif gst_service.id in api_key.allowed_services:
                        has_access = True
                        print(f"\n✅ Access: Has specific access to GST service")
                elif api_key.service_id == gst_service.id:
                    has_access = True
                    print(f"\n✅ Access: Has access via service_id match")
                
                if not has_access:
                    print(f"\n❌ Access: NO ACCESS to GST service")
                    print(f"   Allowed services: {api_key.allowed_services}")
                    print(f"   Service ID: {api_key.service_id}")
                    print(f"   GST Service ID: {gst_service.id}")
            else:
                print(f"\n❌ GST Service not found in database")
            
            # Check whitelist URLs
            if api_key.whitelist_urls:
                print(f"\n🔒 Whitelist URLs: {api_key.whitelist_urls}")
            else:
                print(f"\n🔓 No whitelist URLs (all origins allowed)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_api_key.py <api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    asyncio.run(check_api_key(api_key))

