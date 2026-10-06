import os
import psycopg2
import flet as ft

# --- 1. إعداد قاعدة البيانات السحابية (Supabase) ---
# تم تعديل المنفذ إلى 6543 المتوافق مع Session/Transaction Pooler
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.retdoibqivicmibmzpnd:Arafa.452025.1132000.122000@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"
)

def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            nickname TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            person_id INTEGER,
            amount REAL,
            type TEXT,
            event_name TEXT,
            notes TEXT,
            FOREIGN KEY (person_id) REFERENCES people(id)
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# --- 2. واجهة التطبيق ---
def main(page: ft.Page):
    page.title = "برنامج النقطة والواجب"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    # عناصر الواجهة - الداش بورد
    lbl_total_in = ft.Text("0 ج.م", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)
    lbl_total_out = ft.Text("0 ج.م", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED)
    lbl_net = ft.Text("0 ج.م", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE)

    # عناصر إدخال البيانات
    txt_name = ft.TextField(label="الاسم الكامل", width=300)
    txt_nickname = ft.TextField(label="اسم الشهرة", width=300)
    txt_amount = ft.TextField(label="المبلغ", keyboard_type=ft.KeyboardType.NUMBER, width=300)
    txt_event = ft.TextField(label="المناسبة (مثال: فرحي / فرح هادي)", width=300)
    txt_notes = ft.TextField(label="ملاحظات", multiline=True, width=300)
    
    dropdown_type = ft.Dropdown(
        label="نوع النقطة",
        width=300,
        options=[
            ft.dropdown.Option("IN", "لي (جالي نقطة)"),
            ft.dropdown.Option("OUT", "عليّ (دفعت نقطة)"),
        ],
        value="IN"
    )

    # حقل البحث وقائمة النتائج
    txt_search = ft.TextField(label="بحث بالاسم أو اسم الشهرة", width=300, on_change=lambda e: search_people())
    results_list = ft.ListView(expand=True, spacing=10, height=200)

    # --- تحديث بيانات الداش بورد ---
    def update_dashboard():
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='IN'")
        res_in = cursor.fetchone()[0]
        total_in = res_in if res_in is not None else 0.0
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='OUT'")
        res_out = cursor.fetchone()[0]
        total_out = res_out if res_out is not None else 0.0
        
        net = total_in - total_out
        
        lbl_total_in.value = f"{total_in:,.0f} ج.م"
        lbl_total_out.value = f"{total_out:,.0f} ج.م"
        lbl_net.value = f"{net:,.0f} ج.م"
        page.update()
        cursor.close()
        conn.close()

    # --- حفظ عملية جديدة ---
    def add_transaction(e):
        if not txt_name.value or not txt_amount.value:
            page.open(ft.SnackBar(ft.Text("يرجى إدخال الاسم والمبلغ!")))
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM people WHERE name = %s", (txt_name.value.strip(),))
        person = cursor.fetchone()
        if person:
            person_id = person[0]
        else:
            cursor.execute(
                "INSERT INTO people (name, nickname) VALUES (%s, %s) RETURNING id", 
                (txt_name.value.strip(), txt_nickname.value.strip())
            )
            person_id = cursor.fetchone()[0]

        cursor.execute('''
            INSERT INTO transactions (person_id, amount, type, event_name, notes)
            VALUES (%s, %s, %s, %s, %s)
        ''', (person_id, float(txt_amount.value), dropdown_type.value, txt_event.value, txt_notes.value))

        conn.commit()
        cursor.close()
        conn.close()

        txt_name.value = ""
        txt_nickname.value = ""
        txt_amount.value = ""
        txt_event.value = ""
        txt_notes.value = ""
        
        page.open(ft.SnackBar(ft.Text("تم تسجيل النقطة بنجاح!")))
        update_dashboard()
        search_people()

    # --- البحث في السجلات ---
    def search_people():
        results_list.controls.clear()
        query = txt_search.value.strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.name, p.nickname,
                   COALESCE(SUM(CASE WHEN t.type='IN' THEN t.amount ELSE 0 END), 0) as total_in,
                   COALESCE(SUM(CASE WHEN t.type='OUT' THEN t.amount ELSE 0 END), 0) as total_out
            FROM people p
            LEFT JOIN transactions t ON p.id = t.person_id
            WHERE p.name ILIKE %s OR p.nickname ILIKE %s
            GROUP BY p.id, p.name, p.nickname
        ''', (f'%{query}%', f'%{query}%'))
        
        rows = cursor.fetchall()
        for row in rows:
            p_id, name, nickname, p_in, p_out = row
            balance = p_in - p_out
            
            status_text = f"عليك له: {balance:.0f} ج.م" if balance > 0 else f"له عندك: {abs(balance):.0f} ج.م"
            if balance == 0: status_text = "الحساب متخلص (0)"

            results_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Column([
                            ft.Text(f"{name} ({nickname or 'بدون لقب'})", weight=ft.FontWeight.BOLD),
                            ft.Text(status_text, color=ft.Colors.RED if balance > 0 else ft.Colors.GREEN),
                        ])
                    )
                )
            )
        cursor.close()
        conn.close()
        page.update()

    dashboard_card = ft.Card(
        content=ft.Container(
            padding=15,
            content=ft.Column([
                ft.Text("لوحة التحكم المالية", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([ft.Text("إجمالي ما لي (الوارد):"), lbl_total_in], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("إجمالي ما عليّ (الصادر):"), lbl_total_out], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Row([ft.Text("الصافي العام:"), lbl_net], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ])
        )
    )

    page.add(
        dashboard_card,
        ft.Text("تسجيل نقطة جديدة", size=16, weight=ft.FontWeight.BOLD),
        txt_name,
        txt_nickname,
        txt_amount,
        dropdown_type,
        txt_event,
        txt_notes,
        ft.ElevatedButton("حفظ النقطة", on_click=add_transaction, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE),
        ft.Divider(),
        ft.Text("البحث وكشف الحسابات", size=16, weight=ft.FontWeight.BOLD),
        txt_search,
        results_list
    )

    update_dashboard()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, port=port, view=None)
