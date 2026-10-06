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
    cursor.close()
    conn.close()

init_db()

def main(page: ft.Page):
    page.title = "برنامج النقطة والواجب - نظام الصلاحيات"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = ft.colors.GREY_50

    current_user = {"username": "", "role": ""}

    def show_login_screen():
        page.clean()
        page.appbar = None

        txt_user = ft.TextField(label="اسم المستخدم", filled=True, border_radius=10, prefix_icon=ft.icons.PERSON, width=300)
        txt_pass = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, filled=True, border_radius=10, prefix_icon=ft.icons.LOCK, width=300)

        def handle_login(e):
            u = txt_user.value.strip()
            p = txt_pass.value.strip()
            if not u or not p:
                page.open(ft.SnackBar(ft.Text("يرجى إدخال اسم المستخدم وكلمة المرور!"), bgcolor=ft.colors.RED_400))
                return

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT role FROM users WHERE username = %s AND password = %s", (u, p))
                res = cursor.fetchone()
                cursor.close()
                conn.close()

                if res:
                    current_user["username"] = u
                    current_user["role"] = res[0]
                    show_main_app()
                else:
                    page.open(ft.SnackBar(ft.Text("خطأ في اسم المستخدم أو كلمة المرور!"), bgcolor=ft.colors.RED_400))
            except Exception as ex:
                print("Login error:", ex)

        login_card = ft.Card(
            elevation=5,
            color=ft.colors.WHITE,
            content=ft.Container(
                padding=30,
                content=ft.Column([
                    ft.Icon(ft.icons.LOCK_PERSON, size=50, color=ft.colors.INDIGO_700),
                    ft.Text("تسجيل الدخول للنظام", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_900),
                    ft.Divider(color=ft.colors.INDIGO_100),
                    txt_user,
                    txt_pass,
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "دخول",
                        icon=ft.icons.LOGIN,
                        on_click=handle_login,
                        bgcolor=ft.colors.INDIGO_700,
                        color=ft.colors.WHITE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
                        width=300
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
            )
        )

        page.add(
            ft.View(
                route="/login",
                controls=[
                    ft.Container(
                        content=login_card,
                        alignment=ft.alignment.center,
                        expand=True,
                        bgcolor=ft.colors.GREY_100
                    )
                ]
            )
        )
        page.update()

    def show_main_app():
        page.clean()
        
        page.appbar = ft.AppBar(
            title=ft.Text(f"برنامج النقطة والواجب ({current_user['username']} - {current_user['role']})", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=ft.colors.INDIGO_700,
            actions=[
                ft.IconButton(ft.icons.LOGOUT, tooltip="تسجيل الخروج", icon_color=ft.colors.WHITE, on_click=lambda e: show_login_screen())
            ]
        )

        lbl_total_in = ft.Text("0 ج.م", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_700)
        lbl_total_out = ft.Text("0 ج.م", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.RED_700)
        lbl_net = ft.Text("0 ج.م", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_700)

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

        def open_manage_users_dialog(e):
            new_u = ft.TextField(label="اسم المستخدم الجديد", filled=True, border_radius=10)
            new_p = ft.TextField(label="كلمة المرور", password=True, can_reveal_password=True, filled=True, border_radius=10)
            new_role = ft.Dropdown(
                label="الصلاحية",
                filled=True,
                border_radius=10,
                options=[
                    ft.dropdown.Option("admin", "مدير (Admin)"),
                    ft.dropdown.Option("user", "مستخدم عادي (User)"),
                ],
                value="user"
            )

            def save_new_user(ev):
                if not new_u.value or not new_p.value:
                    return
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (new_u.value.strip(), new_p.value.strip(), new_role.value))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    page.close(dlg_users)
                    page.open(ft.SnackBar(ft.Text("تم إضافة المستخدم بنجاح!"), bgcolor=ft.colors.GREEN_600))
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text("اسم المستخدم موجود مسبقاً أو حدث خطأ!"), bgcolor=ft.colors.RED_400))

            dlg_users = ft.AlertDialog(
                title=ft.Text("إدارة المستخدمين والصلاحيات", weight=ft.FontWeight.BOLD),
                content=ft.Column([new_u, new_p, new_role], tight=True, spacing=10),
                actions=[
                    ft.TextButton("إلغاء", on_click=lambda ev: page.close(dlg_users)),
                    ft.ElevatedButton("حفظ المستخدم", on_click=save_new_user, bgcolor=ft.colors.INDIGO_700, color=ft.colors.WHITE)
                ]
            )
            page.open(dlg_users)

        def show_person_details(person_id, name, nickname):
            def load_details(list_view):
                list_view.controls.clear()
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, amount, type, event_name, notes FROM transactions WHERE person_id = %s", (person_id,))
                    trans_rows = cursor.fetchall()
                    cursor.close()
                    conn.close()

                    for tr in trans_rows:
                        t_id, t_amount, t_type, t_event, t_notes = tr
                        c_color = ft.colors.GREEN_700 if t_type == 'IN' else ft.colors.RED_700
                        txt_desc = f"{'جالي' if t_type=='IN' else 'دفعت'}: {t_amount:,.5g} ج.م | المناسبة: {t_event or 'بدون'}"

                        def delete_trans(e, tid=t_id):
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM transactions WHERE id = %s", (tid,))
                            conn.commit()
                            cursor.close()
                            conn.close()
                            load_details(details_list)
                            update_dashboard()
                            search_people()

                        list_view.controls.append(
                            ft.Container(
                                padding=8,
                                bgcolor=ft.colors.GREY_100,
                                border_radius=8,
                                content=ft.Row([
                                    ft.Column([
                                        ft.Text(txt_desc, weight=ft.FontWeight.BOLD, size=12, color=c_color),
                                        ft.Text(f"ملاحظات: {t_notes or 'لا توجد'}", size=10, color=ft.colors.GREY_600)
                                    ], expand=True),
                                    ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.RED, icon_size=18, on_click=delete_trans, tooltip="حذف الحركة")
                                ])
                            )
                        )
                    if not trans_rows:
                        list_view.controls.append(ft.Text("لا توجد حركات مسجلة."))
                    page.update()
                except Exception as ex:
                    print("Detail error:", ex)

            details_list = ft.ListView(expand=True, spacing=8, height=250)
            load_details(details_list)

            def delete_person(e):
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM people WHERE id = %s", (person_id,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    page.close(dlg_details)
                    update_dashboard()
                    search_people()
                    page.open(ft.SnackBar(ft.Text("تم حذف الشخص وكل معاملاته!"), bgcolor=ft.colors.GREEN_600))
                except Exception as ex:
                    print(ex)

            dlg_details = ft.AlertDialog(
                title=ft.Text(f"سجل: {name} ({nickname or 'بدون لقب'})", size=15, weight=ft.FontWeight.BOLD),
                content=ft.Container(content=details_list, width=400),
                actions=[
                    ft.TextButton("حذف الشخص بالكامل", icon=ft.icons.DELETE_FOREVER, icon_color=ft.colors.RED, on_click=delete_person),
                    ft.TextButton("إغلاق", on_click=lambda e: page.close(dlg_details))
                ]
            )
            page.open(dlg_details)

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
                        status_text = "✨ الحساب خالص تماماً"
                        status_color = ft.colors.BLUE_700

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
                                        ft.Text(f"جالي: {p_in:,.0f} | دفعت: {p_out:,.0f}", size=11, color=ft.colors.GREY_500),
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    ft.Row([
                                        ft.TextButton(
                                            "عرض التفاصيل والحذف",
                                            icon=ft.icons.LIST_ALT,
                                            on_click=lambda e, pid=p_id, pname=name, pnick=nickname: show_person_details(pid, pname, pnick),
                                        )
                                    ], alignment=ft.MainAxisAlignment.END)
                                ])
                            )
                        )
                    )
                cursor.close()
                conn.close()
                page.update()
            except Exception as ex:
                print("Search error:", ex)

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
                    ft.Container(height=5),
                    ft.ElevatedButton(
                        "حفظ النقطة", 
                        icon=ft.icons.SAVE,
                        on_click=add_transaction, 
                        bgcolor=ft.colors.INDIGO_700, 
                        color=ft.colors.WHITE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=15),
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
                    ft.Container(height=10),
                    ft.Container(content=results_list, height=300)
                ], spacing=10)
            )
        )

        controls_list = [dashboard_card, form_card, search_card]

        if current_user["role"] == "admin":
            controls_list.insert(0, ft.ElevatedButton(
                "إدارة المستخدمين والصلاحيات (Admin)",
                icon=ft.icons.ADMIN_PANEL_SETTINGS,
                bgcolor=ft.colors.AMBER_800,
                color=ft.colors.WHITE,
                on_click=open_manage_users_dialog,
                width=float("inf")
            ))

        main_layout = ft.ListView(
            expand=True,
            padding=15,
            spacing=15,
            controls=controls_list
        )

        page.add(main_layout)
        update_dashboard()
        search_people()

    show_login_screen()

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.SUGGESTED_VIEW, port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
