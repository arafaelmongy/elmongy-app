import os
import psycopg
import flet as ft
from fpdf import FPDF
import tempfile

# --- 1. إعداد قاعدة البيانات السحابية (Supabase) ---
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.retdoibqivicmibmzpnd:Arafa.452025.1132000.122000@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"
)

def get_db_connection():
    return psycopg.connect(DB_URL)

def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
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
                        FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL
                    )
                ''')
                
                cursor.execute("SELECT id FROM users WHERE username = 'admin'")
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", ('admin', '123', 'admin'))
            conn.commit()
    except Exception as ex:
        print("Database Init Error:", ex)

init_db()

def main(page: ft.Page):
    page.title = "برنامج النقطة والواجب - نظام الصلاحيات"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = ft.Colors.GREY_50

    current_user = {"username": "", "role": ""}

    def show_login_screen():
        page.clean()
        page.appbar = None

        txt_user = ft.TextField(label="اسم المستخدم", filled=True, border_radius=10, prefix_icon=ft.icons.PERSON, width=300)
        txt_pass = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, filled=True, border_radius=10, prefix_icon=ft.icons.LOCK, width=300)

        def handle_login(e):
            u = txt_user.value.strip() if txt_user.value else ""
            p = txt_pass.value.strip() if txt_pass.value else ""
            if not u or not p:
                page.open(ft.SnackBar(ft.Text("يرجى إدخال اسم المستخدم وكلمة المرور!"), bgcolor=ft.Colors.RED_400))
                return

            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT role FROM users WHERE username = %s AND password = %s", (u, p))
                        res = cursor.fetchone()

                if res:
                    current_user["username"] = u
                    current_user["role"] = res[0]
                    show_main_dashboard()
                else:
                    page.open(ft.SnackBar(ft.Text("خطأ في اسم المستخدم أو كلمة المرور!"), bgcolor=ft.Colors.RED_400))
            except Exception as ex:
                print("Login error:", ex)
                page.open(ft.SnackBar(ft.Text("حدث خطأ أثناء الاتصال بقاعدة البيانات!"), bgcolor=ft.Colors.RED_400))

        login_card = ft.Card(
            elevation=5,
            color=ft.Colors.WHITE,
            content=ft.Container(
                padding=30,
                content=ft.Column([
                    ft.Icon(ft.icons.LOCK_PERSON, size=50, color=ft.Colors.INDIGO_700),
                    ft.Text("تسجيل الدخول للنظام", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_900),
                    ft.Divider(color=ft.Colors.INDIGO_100),
                    txt_user,
                    txt_pass,
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "دخول",
                        icon=ft.icons.LOGIN,
                        on_click=handle_login,
                        bgcolor=ft.Colors.INDIGO_700,
                        color=ft.Colors.WHITE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
                        width=300
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
            )
        )

        page.views.clear()
        page.views.append(
            ft.View(
                route="/login",
                controls=[
                    ft.Container(
                        content=login_card,
                        alignment=ft.alignment.center,
                        expand=True,
                        bgcolor=ft.Colors.GREY_100
                    )
                ]
            )
        )
        page.update()

    def show_main_dashboard():
        page.clean()
        
        page.appbar = ft.AppBar(
            title=ft.Text(f"نقطتي المنجي ({current_user['username']} - {current_user['role']})", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=ft.Colors.INDIGO_700,
            actions=[
                ft.IconButton(ft.icons.LOGOUT, tooltip="تسجيل الخروج", icon_color=ft.Colors.WHITE, on_click=lambda e: show_login_screen())
            ]
        )

        lbl_total_in = ft.Text("0 ج.م", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        lbl_total_out = ft.Text("0 ج.م", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)

        def update_totals():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='IN'")
                        res_in = cursor.fetchone()[0]
                        total_in = res_in if res_in is not None else 0.0
                        
                        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='OUT'")
                        res_out = cursor.fetchone()[0]
                        total_out = res_out if res_out is not None else 0.0
                
                lbl_total_in.value = f"{total_in:,.0f} ج.م"
                lbl_total_out.value = f"{total_out:,.0f} ج.م"
                page.update()
            except Exception as ex:
                print("Dashboard Error:", ex)

        dashboard_card = ft.Card(
            elevation=4,
            color=ft.Colors.WHITE,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.DASHBOARD, color=ft.Colors.INDIGO_700),
                        ft.Text("لوحة التحكم المالية", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_700),
                    ]),
                    ft.Divider(color=ft.Colors.INDIGO_100),
                    ft.Row([ft.Text("إجمالي الوارد:", color=ft.Colors.GREY_700, size=16), lbl_total_in], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(color=ft.Colors.GREY_200),
                    ft.Row([ft.Text("إجمالي الصادر:", color=ft.Colors.GREY_700, size=16), lbl_total_out], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ], spacing=15)
            )
        )

        user_role = current_user["role"]
        is_read_only = (user_role == "read_only")

        btn_add_in = ft.ElevatedButton(
            "إضافة نقطة (وارد)",
            icon=ft.icons.ADD_CIRCLE,
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
            width=float("inf"),
            on_click=lambda e: show_add_transaction_page("IN"),
            disabled=is_read_only
        )

        btn_add_out = ft.ElevatedButton(
            "إضافة صادر",
            icon=ft.icons.REMOVE_CIRCLE,
            bgcolor=ft.Colors.RED_700,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
            width=float("inf"),
            on_click=lambda e: show_add_transaction_page("OUT"),
            disabled=is_read_only
        )

        btn_list_in = ft.ElevatedButton(
            "حصر أسماء النقطة الواردة",
            icon=ft.icons.LIST_ALT,
            bgcolor=ft.Colors.TEAL_700,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
            width=float("inf"),
            on_click=lambda e: show_report_page("IN")
        )

        btn_list_out = ft.ElevatedButton(
            "حصر الصادر",
            icon=ft.icons.FORMAT_LIST_BULLETED,
            bgcolor=ft.Colors.ORANGE_800,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
            width=float("inf"),
            on_click=lambda e: show_report_page("OUT")
        )

        btn_search = ft.ElevatedButton(
            "بحث وكشف الحسابات",
            icon=ft.icons.SEARCH,
            bgcolor=ft.Colors.INDIGO_700,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
            width=float("inf"),
            on_click=lambda e: show_search_page()
        )

        controls_list = [dashboard_card, btn_add_in, btn_add_out, btn_list_in, btn_list_out, btn_search]

        if user_role == "admin" or user_role == "manage_users":
            btn_users = ft.ElevatedButton(
                "إدارة المستخدمين والصلاحيات",
                icon=ft.icons.ADMIN_PANEL_SETTINGS,
                bgcolor=ft.Colors.AMBER_800,
                color=ft.Colors.WHITE,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
                width=float("inf"),
                on_click=lambda e: open_manage_users_dialog(e)
            )
            controls_list.append(btn_users)

        main_layout = ft.ListView(
            expand=True,
            padding=20,
            spacing=15,
            controls=controls_list
        )

        page.views.clear()
        page.views.append(
            ft.View(
                route="/main",
                appbar=page.appbar,
                controls=[main_layout]
            )
        )
        page.update()
        update_totals()

    def show_add_transaction_page(t_type):
        title_text = "إضافة نقطة (واردة)" if t_type == "IN" else "إضافة صادر"
        
        txt_name = ft.TextField(label="الاسم الكامل", filled=True, border_radius=10, prefix_icon=ft.icons.PERSON)
        txt_nickname = ft.TextField(label="اسم الشهرة", filled=True, border_radius=10, prefix_icon=ft.icons.TAG)
        txt_amount = ft.TextField(label="المبلغ (ج.م)", keyboard_type=ft.KeyboardType.NUMBER, filled=True, border_radius=10, prefix_icon=ft.icons.MONETIZATION_ON)
        txt_event = ft.TextField(label="المناسبة", filled=True, border_radius=10, prefix_icon=ft.icons.EVENT)
        txt_notes = ft.TextField(label="ملاحظات إضافية", multiline=True, min_lines=2, max_lines=4, filled=True, border_radius=10, prefix_icon=ft.icons.NOTE)

        def save_trans(e):
            if not txt_name.value or not txt_amount.value:
                page.open(ft.SnackBar(ft.Text("يرجى إدخال الاسم والمبلغ على الأقل!"), bgcolor=ft.Colors.RED_400))
                return
            try:
                amount_val = float(txt_amount.value)
            except ValueError:
                page.open(ft.SnackBar(ft.Text("يرجى إدخال مبلغ صحيح!"), bgcolor=ft.Colors.RED_400))
                return

            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
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
                        ''', (person_id, amount_val, t_type, txt_event.value, txt_notes.value))
                        conn.commit()

                page.open(ft.SnackBar(ft.Text("تم الحفظ بنجاح! 🎉"), bgcolor=ft.Colors.GREEN_600))
                show_main_dashboard()
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"حدث خطأ: {ex}"), bgcolor=ft.Colors.RED_400))

        form_content = ft.Column([
            ft.Text(title_text, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_900),
            ft.Divider(),
            txt_name,
            txt_nickname,
            txt_amount,
            txt_event,
            txt_notes,
            ft.Container(height=10),
            ft.ElevatedButton("حفظ", icon=ft.icons.SAVE, on_click=save_trans, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, width=float("inf"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15)),
            ft.ElevatedButton("رجوع", icon=ft.icons.ARROW_BACK, on_click=lambda e: show_main_dashboard(), bgcolor=ft.Colors.GREY_700, color=ft.Colors.WHITE, width=float("inf"), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15))
        ], spacing=15)

        page.views.clear()
        page.views.append(
            ft.View(
                route="/add_trans",
                appbar=ft.AppBar(title=ft.Text(title_text, color=ft.Colors.WHITE), bgcolor=ft.Colors.INDIGO_700),
                controls=[ft.Container(content=form_content, padding=20)]
            )
        )
        page.update()

    def show_report_page(t_type):
        title_text = "حصر أسماء النقطة الواردة" if t_type == "IN" else "حصر الصادر"
        report_list = ft.ListView(expand=True, spacing=10)
        rows_data = []

        def load_report():
            nonlocal rows_data
            report_list.controls.clear()
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute('''
                            SELECT p.name, p.nickname, t.amount, t.event_name, t.notes
                            FROM transactions t
                            JOIN people p ON t.person_id = p.id
                            WHERE t.type = %s
                            ORDER BY p.name ASC
                        ''', (t_type,))
                        rows_data = cursor.fetchall()

                for r in rows_data:
                    p_name, p_nick, amount, event_n, notes = r
                    report_list.controls.append(
                        ft.Card(
                            content=ft.Container(
                                padding=12,
                                content=ft.Column([
                                    ft.Row([ft.Text(f"الاسم: {p_name}", weight=ft.FontWeight.BOLD), ft.Text(f"الشهرة: {p_nick or 'بدون'}", color=ft.Colors.GREY_700)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    ft.Row([ft.Text(f"المبلغ: {amount:,.0f} ج.م", color=ft.Colors.GREEN_700 if t_type=='IN' else ft.Colors.RED_700, weight=ft.FontWeight.BOLD), ft.Text(f"المناسبة: {event_n or 'بدون'}")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    ft.Text(f"ملاحظات: {notes or 'لا توجد'}", size=12, color=ft.Colors.GREY_600)
                                ], spacing=5)
                            )
                        )
                    )
                if not rows_data:
                    report_list.controls.append(ft.Text("لا توجد بيانات مسجلة."))
                page.update()
            except Exception as ex:
                print("Report error:", ex)

        load_report()

        def export_pdf_only(e):
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 12)
                
                # استخدام عناوين إنجليزية آمنة لتفادي أخطاء الترميز
                pdf.cell(200, 10, txt="Financial Report - Elmongy App", ln=True, align="C")
                pdf.ln(10)
                
                pdf.set_font("Arial", "", 10)
                for r in rows_data:
                    p_name, p_nick, amount, event_n, notes = r
                    # تنظيف النصوص العربية وتحويلها لتفادي خطأ latin-1 أو استبدالها بترميز آمن
                    safe_name = str(p_name).encode('latin-1', 'replace').decode('latin-1')
                    safe_nick = str(p_nick or '-').encode('latin-1', 'replace').decode('latin-1')
                    safe_event = str(event_n or '-').encode('latin-1', 'replace').decode('latin-1')
                    
                    line_text = f"Name: {safe_name} | Nick: {safe_nick} | Amount: {amount} LE | Event: {safe_event}"
                    pdf.cell(200, 8, txt=line_text, ln=True)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    pdf.output(tmp.name)
                    page.launch_url(tmp.name)
                
                page.open(ft.SnackBar(ft.Text("تم إنشاء وحفظ ملف الـ PDF بنجاح! 📄"), bgcolor=ft.Colors.GREEN_600))
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"خطأ أثناء تصدير الـ PDF: {ex}"), bgcolor=ft.Colors.RED_400))

        page.views.clear()
        page.views.append(
            ft.View(
                route="/report",
                appbar=ft.AppBar(title=ft.Text(title_text, color=ft.Colors.WHITE), bgcolor=ft.Colors.INDIGO_700),
                controls=[
                    ft.Container(
                        padding=15,
                        content=ft.Column([
                            ft.Row([
                                ft.ElevatedButton("حفظ كشف PDF فقط", icon=ft.icons.PICTURE_AS_PDF, on_click=export_pdf_only, bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE),
                                ft.ElevatedButton("رجوع", icon=ft.icons.ARROW_BACK, on_click=lambda e: show_main_dashboard(), bgcolor=ft.Colors.GREY_700, color=ft.Colors.WHITE)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Divider(),
                            ft.Container(content=report_list, expand=True)
                        ], expand=True)
                    )
                ]
            )
        )
        page.update()

    def show_search_page():
        txt_search = ft.TextField(label="اكتب اسم الشخص للبحث...", filled=True, border_radius=10, prefix_icon=ft.icons.SEARCH)
        results_col = ft.ListView(expand=True, spacing=10)

        def execute_search(e):
            results_col.controls.clear()
            q = txt_search.value.strip() if txt_search.value else ""
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute('''
                            SELECT p.id, p.name, p.nickname,
                                   COALESCE(SUM(CASE WHEN t.type='IN' THEN t.amount ELSE 0 END), 0) as total_in,
                                   COALESCE(SUM(CASE WHEN t.type='OUT' THEN t.amount ELSE 0 END), 0) as total_out
                            FROM people p
                            LEFT JOIN transactions t ON p.id = t.person_id
                            WHERE p.name ILIKE %s OR p.nickname ILIKE %s
                            GROUP BY p.id, p.name, p.nickname
                            ORDER BY p.name ASC
                        ''', (f'%{q}%', f'%{q}%'))
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
                        status_text = "✨ تم الانتهاء أو التصفية (خالص تماماً)"
                        status_color = ft.colors.BLUE_700

                    def make_action(pid, pname, ptype):
                        return lambda ev: open_quick_trans_dialog(pid, pname, ptype)

                    results_col.controls.append(
                        ft.Card(
                            content=ft.Container(
                                padding=15,
                                content=ft.Column([
                                    ft.Row([ft.Text(name, weight=ft.FontWeight.BOLD, size=16), ft.Text(f"({nickname or 'بدون'})", color=ft.Colors.GREY_600)], alignment=ft.MainAxisAlignment.START),
                                    ft.Divider(height=1),
                                    ft.Text(status_text, weight=ft.FontWeight.BOLD, color=status_color),
                                    ft.Row([
                                        ft.ElevatedButton("إضافة وارد", icon=ft.icons.ADD, on_click=make_action(p_id, name, "IN"), bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                                        ft.ElevatedButton("إضافة صادر", icon=ft.icons.REMOVE, on_click=make_action(p_id, name, "OUT"), bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                                ], spacing=8)
                            )
                        )
                    )
                if not rows:
                    results_col.controls.append(ft.Text("لا توجد نتائج مطابقة للبحث."))
                page.update()
            except Exception as ex:
                print("Search error:", ex)

        txt_search.on_change = execute_search

        def open_quick_trans_dialog(pid, pname, ttype):
            t_amount_box = ft.TextField(label="المبلغ", keyboard_type=ft.KeyboardType.NUMBER, filled=True)
            t_event_box = ft.TextField(label="المناسبة", filled=True)
            
            def save_quick(ev):
                try:
                    amt = float(t_amount_box.value)
                    with get_db_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("INSERT INTO transactions (person_id, amount, type, event_name) VALUES (%s, %s, %s, %s)", (pid, amt, ttype, t_event_box.value))
                            conn.commit()
                    page.close(dlg_quick)
                    page.open(ft.SnackBar(ft.Text("تمت العملية بنجاح وتحديث الحساب!"), bgcolor=ft.Colors.GREEN_600))
                    execute_search(None)
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text(f"خطأ: {ex}"), bgcolor=ft.Colors.RED_400))

            dlg_quick = ft.AlertDialog(
                title=ft.Text(f"تسجيل {'وارد' if ttype=='IN' else 'صادر'} لـ {pname}"),
                content=ft.Column([t_amount_box, t_event_box], tight=True),
                actions=[
                    ft.TextButton("إلغاء", on_click=lambda ev: page.close(dlg_quick)),
                    ft.ElevatedButton("حفظ وتعديل الرصيد", on_click=save_quick, bgcolor=ft.Colors.INDIGO_700, color=ft.Colors.WHITE)
                ]
            )
            page.open(dlg_quick)

        execute_search(None)

        page.views.clear()
        page.views.append(
            ft.View(
                route="/search",
                appbar=ft.AppBar(title=ft.Text("البحث وكشف الحسابات", color=ft.Colors.WHITE), bgcolor=ft.Colors.INDIGO_700),
                controls=[
                    ft.Container(
                        padding=15,
                        content=ft.Column([
                            ft.Row([
                                ft.ElevatedButton("رجوع", icon=ft.icons.ARROW_BACK, on_click=lambda e: show_main_dashboard(), bgcolor=ft.Colors.GREY_700, color=ft.Colors.WHITE)
                            ]),
                            txt_search,
                            ft.Container(height=10),
                            ft.Container(content=results_col, expand=True)
                        ], expand=True)
                    )
                ]
            )
        )
        page.update()

    def open_manage_users_dialog(e):
        users_list_col = ft.ListView(expand=True, spacing=10, height=200)
        txt_user_search = ft.TextField(label="بحث عن مستخدم...", filled=True, border_radius=10, dense=True)

        def load_users_list(query=""):
            users_list_col.controls.clear()
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT id, username, role, password FROM users WHERE username ILIKE %s", (f'%{query}%',))
                        users = cursor.fetchall()

                for u_id, uname, urole, upass in users:
                    u_pass_field = ft.TextField(value=upass, label="كلمة المرور الجديدة", password=True, can_reveal_password=True, dense=True)
                    r_dropdown = ft.Dropdown(
                        value=urole,
                        dense=True,
                        options=[
                            ft.dropdown.Option("admin", "مدير"),
                            ft.dropdown.Option("edit", "تعديل"),
                            ft.dropdown.Option("read_only", "قراءة فقط"),
                        ]
                    )

                    users_list_col.controls.append(
                        ft.Card(
                            content=ft.Container(
                                padding=10,
                                content=ft.Column([
                                    ft.Text(f"المستخدم: {uname}", weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_900),
                                    u_pass_field,
                                    r_dropdown,
                                    ft.ElevatedButton("حفظ التعديل", icon=ft.icons.SAVE, on_click=lambda ev, uid=u_id, up=u_pass_field, rd=r_dropdown: save_user_changes(uid, up.value, rd.value), bgcolor=ft.Colors.INDIGO_700, color=ft.Colors.WHITE)
                                ], spacing=5)
                            )
                        )
                    )
                page.update()
            except Exception as ex:
                print("Load users error:", ex)

        def save_user_changes(uid, new_pass, new_role):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("UPDATE users SET password = %s, role = %s WHERE id = %s", (new_pass.strip(), new_role, uid))
                        conn.commit()
                page.open(ft.SnackBar(ft.Text("تم تعديل بيانات المستخدم بنجاح!"), bgcolor=ft.Colors.GREEN_600))
                load_users_list(txt_user_search.value)
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"خطأ: {ex}"), bgcolor=ft.Colors.RED_400))

        txt_user_search.on_change = lambda ev: load_users_list(txt_user_search.value)
        load_users_list()

        new_u = ft.TextField(label="اسم المستخدم الجديد", filled=True, border_radius=10, dense=True)
        new_p = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, filled=True, border_radius=10, dense=True)
        new_role = ft.Dropdown(
            label="تحديد الصلاحيات",
            filled=True,
            border_radius=10,
            dense=True,
            options=[
                ft.dropdown.Option("admin", "مدير كامل الصلاحيات (Admin)"),
                ft.dropdown.Option("edit", "تعديل وحذف وإضافة"),
                ft.dropdown.Option("read_only", "قراءة فقط وبحث"),
            ],
            value="read_only"
        )

        def save_new_user(ev):
            if not new_u.value or not new_p.value:
                return
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (new_u.value.strip(), new_p.value.strip(), new_role.value))
                        conn.commit()
                new_u.value = ""
                new_p.value = ""
                load_users_list()
                page.open(ft.SnackBar(ft.Text("تم إضافة المستخدم وصلاحياته بنجاح!"), bgcolor=ft.Colors.GREEN_600))
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text("اسم المستخدم موجود مسبقاً أو حدث خطأ!"), bgcolor=ft.Colors.RED_400))

        dlg_users = ft.AlertDialog(
            title=ft.Text("إدارة المستخدمين والبحث", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("إضافة مستخدم جديد:", weight=ft.FontWeight.BOLD, size=14),
                new_u, new_p, new_role,
                ft.ElevatedButton("حفظ المستخدم الجديد", on_click=save_new_user, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                ft.Divider(),
                ft.Text("بحث وتعديل المستخدمين الحاليين:", weight=ft.FontWeight.BOLD, size=14),
                txt_user_search,
                users_list_col
            ], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("إغلاق", on_click=lambda ev: page.close(dlg_users))
            ]
        )
        page.open(dlg_users)

    show_login_screen()

if __name__ == "__main__":
    ft.app(target=main, port=int(os.environ.get("PORT", 8080)))
