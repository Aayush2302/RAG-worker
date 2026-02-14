# config/supabase.py
from supabase import create_client, Client
from src.config.env import env

"""
Supabase Admin Client
Uses service_role key to bypass RLS
ONLY use on backend - never expose to frontend
"""

supabase_admin: Client = create_client(
    env.SUPABASE_URL,
    env.SUPABASE_SERVICE_ROLE_KEY
)


print('✅ Supabase Admin Client initialized')