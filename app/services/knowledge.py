from app.database import supabase

def build_knowledge_base(shop_id: str) -> str:
    """
    ดึงข้อมูลทั้งหมดของร้านมาสร้างเป็น text
    สำหรับใส่ใน Gemini context cache
    """
    kb_parts = []

    # สินค้า
    products = supabase.table("products")\
        .select("name, description, price, stock")\
        .eq("shop_id", shop_id)\
        .eq("is_active", True)\
        .execute().data

    if products:
        kb_parts.append("=== สินค้าของร้าน ===")
        for p in products:
            stock_status = f"มีสินค้า {p['stock']} ชิ้น" if p['stock'] > 0 else "สินค้าหมด"
            kb_parts.append(
                f"- {p['name']}: {p['description'] or ''} "
                f"ราคา {p['price']} บาท ({stock_status})"
            )

    # FAQ
    faqs = supabase.table("faqs")\
        .select("question, answer")\
        .eq("shop_id", shop_id)\
        .eq("is_active", True)\
        .execute().data

    if faqs:
        kb_parts.append("\n=== คำถามที่พบบ่อย ===")
        for f in faqs:
            kb_parts.append(f"Q: {f['question']}\nA: {f['answer']}")

    # นโยบาย
    policy = supabase.table("shop_policies")\
        .select("*")\
        .eq("shop_id", shop_id)\
        .execute().data

    if policy:
        p = policy[0]
        kb_parts.append("\n=== นโยบายร้าน ===")
        if p.get("shipping_policy"):
            kb_parts.append(f"การจัดส่ง: {p['shipping_policy']}")
        if p.get("return_policy"):
            kb_parts.append(f"การคืนสินค้า: {p['return_policy']}")
        if p.get("payment_methods"):
            kb_parts.append(f"ช่องทางชำระเงิน: {p['payment_methods']}")
        if p.get("business_hours"):
            kb_parts.append(f"เวลาทำการ: {p['business_hours']}")
        if p.get("about"):
            kb_parts.append(f"ประวัติและข้อมูลร้าน: {p['about']}")

    return "\n".join(kb_parts)