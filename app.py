import os
import psycopg
import flet as ft

# --- 1. إعداد قاعدة البيانات السحابية (Supabase) ---
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.retdoibqivicmibmzpnd:Arafa.452025.1132000.122000@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"
)

def get_db_connection():
    return psycopg.connect(DB_URL)

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

# --- 2. واجهة التطبيق المحسنة ---
def main(page: ft.Page):
    page.title = "برنامج النقطة والواجب"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = ft.colors.GREY_50

    # شريط علوي عصري
    page.appbar = ft.AppBar(
        title=ft.Text("برنامج النقطة والواجب", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.colors.INDIGO_700,
    )

    lbl_total_in = ft.Text("0 ج.م", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_700)
    lbl_total_out = ft.Text("0 ج.م", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.RED_700)
    lbl_net = ft.Text("0 ج.م", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_700)

    # عناصر إدخال البيانات بتصميم عصري وخلفية بارزة
    txt_name = ft.TextField(label="الاسم الكامل", filled=True, border_radius=10, prefix_icon=ft.icons.PERSON)
    txt_nickname = ft.TextField(label="اسم الشهرة", filled=True, border_radius=10, prefix_icon=ft.icons.TAG)
    txt_amount = ft.TextField(label="المبلغ (ج.م)", keyboard_type=ft.KeyboardType.NUMBER, filled=True, border_radius=10, prefix_icon=ft.icons.MONETIZATION_ON)
    txt_event = ft.TextField(label="المناسبة (مثال: فرحي / فرح هادي)", filled=True, border_radius=10, prefix_icon=ft.icons.EVENT)
    txt_notes = ft.TextField(label="ملاحظات إضافية", multiline=True, min_lines=2, max_lines=4, filled=True, border_radius=10, prefix_icon=ft.icons.NOTE)
    
    dropdown_type = ft.Dropdown(
        label="نوع النقطة",
        filled=True,
        border_radius=10,
        prefix_icon=ft.icons.SWAP_HORIZ,
        options=[
            ft.dropdown.Option("IN", "لي (جالي نقطة)"),
            ft.dropdown.Option("OUT", "عليّ (دفعت نقطة)"),
        ],
        value="IN"
    )

    txt_search = ft.TextField(label="بحث بالاسم أو اسم الشهرة...", filled=True, border_radius=10, prefix_icon=ft.icons.SEARCH, on_change=lambda e: search_people())
    results_list = ft.ListView(expand=True, spacing=10, padding=5)

    # --- تحديث بيانات لوحة التحكم ---
    def update_dashboard():
        try:
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
        except Exception as ex:
            print("Error:", ex)

    # --- حفظ معاملة جديدة ---
    def add_transaction(e):
        if not txt_name.value or not txt_amount.value:
            page.open(ft.SnackBar(ft.Text("يرجى إدخال الاسم والمبلغ على الأقل!"), bgcolor=ft.colors.RED_400))
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM people WHERE name = %s", (txt_name.value.strip(),))
            person = cursor.fetchone()
            if person:
                person_id = person[0]
            else:
                cursor.execute(
                    "INSERT INTO people (name, nickname) VALUES (%s, %s) RETURNING id", 
                    (txt_name.value.strip(), txt_nickname.value.strip() if txt_nickname.value else "")
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
            
            page.open(ft.SnackBar(ft.Text("تم تسجيل النقطة بنجاح! 🎉"), bgcolor=ft.colors.GREEN_600))
            update_dashboard()
            search_people()
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"حدث خطأ: {ex}"), bgcolor=ft.colors.RED_400))

    # --- البحث ---
    def search_people():
        results_list.controls.clear()
        query = txt_search.value.strip() if txt_search.value else ""
        
        try:
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
                ORDER BY p.name ASC
            ''', (f'%{query}%', f'%{query}%'))
            
            rows = cursor.fetchall()
            for row in rows:
                p_id, name, nickname, p_in, p_out = row
                balance = p_in - p_out
                
                if balance > 0:
                    status_text = f"عليك له: {balance:,.0f} ج.م"
                    status_color = ft.colors.RED_700
                elif balance < 0:
                    status_text = f"له عندك: {abs(balance):,.0f} ج.م"
                    status_color = ft.colors.GREEN_700
                else:
                    status_text = "الحساب متخلص تماماً (0)"
                    status_color = ft.colors.GREY_700

                results_list.controls.append(
                    ft.Card(
                        elevation=2,
                        color=ft.colors.WHITE,
                        content=ft.Container(
                            padding=15,
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"{name}", weight=ft.FontWeight.BOLD, size=16, color=ft.colors.INDIGO_900),
                                    ft.Text(f"({nickname or 'بدون لقب'})", size=12, color=ft.colors.GREY_600),
                                ], alignment=ft.MainAxisAlignment.START),
                                ft.Divider(height=1, color=ft.colors.GREY_200),
                                ft.Row([
                                    ft.Text(status_text, weight=ft.FontWeight.BOLD, color=status_color),
                                    ft.Text(f"وارد: {p_in:,.0f} | صادر: {p_out:,.0f}", size=11, color=ft.colors.GREY_500),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ])
                        )
                    )
                )
            cursor.close()
            conn.close()
            page.update()
        except Exception as ex:
            print("Search error:", ex)

    # --- بناء الواجهة عبر البطاقات المنظمة ---
    dashboard_card = ft.Card(
        elevation=4,
        color=ft.colors.WHITE,
        content=ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.DASHBOARD, color=ft.colors.INDIGO_700),
                    ft.Text("لوحة التحكم المالية", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_700),
                ]),
                ft.Divider(color=ft.colors.INDIGO_100),
                ft.Row([ft.Text("إجمالي ما لي (الوارد):", color=ft.colors.GREY_700), lbl_total_in], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("إجمالي ما عليّ (الصادر):", color=ft.colors.GREY_700), lbl_total_out], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color=ft.colors.INDIGO_100),
                ft.Row([ft.Text("الصافي العام:", weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_900), lbl_net], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ])
        )
    )

    form_card = ft.Card(
        elevation=4,
        color=ft.colors.WHITE,
        content=ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.POST_ADD, color=ft.colors.INDIGO_700),
                    ft.Text("تسجيل نقطة جديدة", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_700),
                ]),
                ft.Divider(color=ft.colors.INDIGO_100),
                txt_name,
                txt_nickname,
                txt_amount,
                dropdown_type,
                txt_event,
                txt_notes,
                ft.SizedBox(height: 5),
                ft.ElevatedButton(
                    "حفظ النقطة", 
                    icon=ft.icons.SAVE,
                    on_click=add_transaction, 
                    bgcolor=ft.colors.INDIGO_700, 
                    color=ft.colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=15
                    ),
                    width=float("inf")
                ),
            ], spacing=12)
        )
    )

    search_card = ft.Card(
        elevation=4,
        color=ft.colors.WHITE,
        content=ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.SEARCH, color=ft.colors.INDIGO_700),
                    ft.Text("البحث وكشف الحسابات", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_700),
                ]),
                ft.Divider(color=ft.colors.INDIGO_100),
                txt_search,
                ft.SizedBox(height: 10),
                ft.Container(content=results_list, height=260)
            ], spacing=10)
        )
    )

    main_layout = ft.ListView(
        expand=True,
        padding=15,
        spacing=15,
        controls=[
            dashboard_card,
            form_card,
            search_card
        ]
    )

    page.add(main_layout)
    update_dashboard()
    search_people()

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8080)))
