from supabase import create_client, Client
from app.config import settings

# สร้าง Connection ไปยัง Supabase
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)