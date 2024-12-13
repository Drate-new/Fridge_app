import tkinter as tk
from tkinter import messagebox
import psycopg2
import re

# Подключение к базе данных
def connect_db():
    try:
        connection = psycopg2.connect(
            dbname="My_fridge_app",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        return connection
    except Exception as e:
        messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к базе данных: {e}")
        return None

db_connection = connect_db()
current_user_id = None  # Переменная для хранения текущего пользователя

# Очистка окна
def clear_window(frame):
    for widget in frame.winfo_children():
        widget.destroy()

# Возврат на главный экран
def return_to_main(frame):
    global current_user_id
    current_user_id = None
    clear_window(frame)
    main_screen(frame)

# Проверка пароля
def validate_password(password):
    if len(password) < 5:
        return "Пароль должен содержать не менее 5 символов"
    if not re.search(r'[A-Za-z]', password):
        return "Пароль должен содержать хотя бы одну латинскую букву"
    if not re.search(r'[0-9]', password):
        return "Пароль должен содержать хотя бы одну цифру"
    return None

# Логика входа
def login_action(login, password, frame):
    global current_user_id, current_username
    try:
        cursor = db_connection.cursor()
        cursor.execute("SELECT user_id, username, password_hash, imt FROM public.app_users WHERE login = %s", (login,))
        result = cursor.fetchone()

        if result and result[2] == password:
            current_user_id = result[0]
            current_username = result[1]

            # Проверка ИМТ
            imt = result[3]
            if imt:
                if imt > 25:
                    messagebox.showinfo("Совет", "Мы рекомендуем уменьшить количество быстрых углеводов в вашем рационе.")
                elif imt < 18.5:
                    messagebox.showinfo("Совет", "Мы рекомендуем увеличить количество калорий в вашем рационе.")

            show_user_menu(frame)
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при входе: {e}")

# Меню после входа
def show_user_menu(frame):
    clear_window(frame)

    tk.Label(frame, text="Что вы хотите сделать?", font=("Arial", 14)).pack(pady=10)
    tk.Button(frame, text="Посмотреть свои холодильники", font=("Arial", 12), command=lambda: show_fridges(frame)).pack(pady=10)
    tk.Button(frame, text="Посмотреть свои данные", font=("Arial", 12), command=lambda: show_user_data(frame)).pack(pady=10)
    tk.Button(frame, text="Выйти из аккаунта", font=("Arial", 12), command=lambda: return_to_main(frame)).pack(pady=10)

def add_product_to_fridge(fridge_id, frame):
    clear_window(frame)

    tk.Label(frame, text="Введите название продукта:", font=("Arial", 12)).pack(pady=5)
    product_name_entry = tk.Entry(frame, font=("Arial", 12))
    product_name_entry.pack()

    tk.Label(frame, text="Введите количество:", font=("Arial", 12)).pack(pady=5)
    quantity_entry = tk.Entry(frame, font=("Arial", 12))
    quantity_entry.pack()

    def add_product_action():
        product_name = product_name_entry.get().strip()
        quantity = quantity_entry.get().strip()

        if not product_name or not quantity:
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены!")
            return

        try:
            cursor = db_connection.cursor()
            cursor.execute("BEGIN")
            cursor.execute("""
                INSERT INTO public.products (product_name) VALUES (%s) RETURNING product_id
            """, (product_name,))
            product_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO public.fridge_content (fridge_id, product_id, quantity_exist)
                VALUES (%s, %s, %s)
            """, (fridge_id, product_id, quantity))
            db_connection.commit()
            messagebox.showinfo("Успешно", "Продукт добавлен!")
            show_fridge_products(fridge_id, frame)
        except Exception as e:
            db_connection.rollback()
            messagebox.showerror("Ошибка", f"Не удалось добавить продукт: {e}")

    tk.Button(frame, text="Добавить", font=("Arial", 12), command=add_product_action).pack(pady=10)
    tk.Button(frame, text="Назад", font=("Arial", 12), command=lambda: show_fridge_products(fridge_id, frame)).pack(pady=5)

def show_fridge_products(fridge_id, frame):
    clear_window(frame)

    try:
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT p.product_id, p.product_name, fc.quantity_exist
            FROM public.fridge_content fc
            JOIN public.products p ON fc.product_id = p.product_id
            WHERE fc.fridge_id = %s AND fc.quantity_exist > 0
        """, (fridge_id,))
        products = cursor.fetchall()

        if products:
            tk.Label(frame, text="Продукты в холодильнике:", font=("Arial", 14)).pack(pady=10)
            for product_id, product_name, quantity_exist in products:
                tk.Label(frame, text=f"{product_name} (Кол-во: {quantity_exist})", font=("Arial", 12)).pack(anchor="w", padx=20)
        else:
            tk.Label(frame, text="В этом холодильнике нет продуктов.", font=("Arial", 14)).pack(pady=20)

        tk.Button(frame, text="Назад", font=("Arial", 12), command=lambda: show_fridges(frame)).pack(pady=10)

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить продукты: {e}")


def delete_fridge(fridge_id, frame):
    try:
        cursor = db_connection.cursor()
        cursor.execute("BEGIN")  # Начало транзакции

        # Удаление связанных записей из fridge_content
        cursor.execute("DELETE FROM public.fridge_content WHERE fridge_id = %s", (fridge_id,))

        # Удаление связанных записей из user_fridge_access
        cursor.execute("DELETE FROM public.user_fridge_access WHERE fridge_id = %s", (fridge_id,))

        # Удаление самого холодильника
        cursor.execute("DELETE FROM public.fridges WHERE fridge_id = %s", (fridge_id,))

        db_connection.commit()
        messagebox.showinfo("Успешно", "Холодильник и связанные данные удалены!")
        show_fridges(frame)
    except Exception as e:
        db_connection.rollback()
        messagebox.showerror("Ошибка", f"Не удалось удалить холодильник: {e}")

# Просмотр холодильников
def show_fridges(frame):
    clear_window(frame)

    try:
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT f.fridge_id, f.fridge_name, f.cost_total, f.calories_total, ufa.user_role
            FROM public.fridges f
            JOIN public.user_fridge_access ufa ON f.fridge_id = ufa.fridge_id
            WHERE ufa.user_id = %s
        """, (current_user_id,))
        fridges = cursor.fetchall()

        if fridges:
            tk.Label(frame, text="Ваши холодильники:", font=("Arial", 14)).pack(pady=10)
            for fridge_id, fridge_name, cost_total, calories_total, user_role in fridges:
                frame_fridge = tk.Frame(frame)
                frame_fridge.pack(fill="x", pady=5)

                tk.Label(frame_fridge, text=f"{fridge_name} (ID: {fridge_id})", font=("Arial", 12)).pack(side="left")
                tk.Label(frame_fridge, text=f"Стоимость: {cost_total} | Калории: {calories_total}", font=("Arial", 10)).pack(side="left")

                # Кнопка перехода к продуктам
                tk.Button(frame_fridge, text="Открыть", font=("Arial", 10),
                          command=lambda fid=fridge_id: show_fridge_products(fid, frame)).pack(side="right")

                # Кнопка удаления холодильника
                if user_role == "O":
                    tk.Button(frame_fridge, text="Удалить", font=("Arial", 10),
                              command=lambda fid=fridge_id: delete_fridge(fid, frame)).pack(side="right")
        else:
            tk.Label(frame, text="У вас нет холодильников", font=("Arial", 14)).pack(pady=20)

        tk.Button(frame, text="Назад", font=("Arial", 12), command=lambda: show_user_menu(frame)).pack(pady=10)

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить холодильники: {e}")

# Добавление холодильника
def add_fridge(frame):
    clear_window(frame)

    tk.Label(frame, text="Введите название нового холодильника:", font=("Arial", 12)).pack(pady=10)
    fridge_name_entry = tk.Entry(frame, font=("Arial", 12))
    fridge_name_entry.pack()

    def add_fridge_action():
        fridge_name = fridge_name_entry.get().strip()
        if not fridge_name:
            messagebox.showerror("Ошибка", "Название холодильника не может быть пустым!")
            return
        try:
            cursor = db_connection.cursor()
            cursor.execute("BEGIN")
            cursor.execute("""
                        CALL public.add_new_fridge(%s, %s)
                    """, (fridge_name, current_user_id))
            db_connection.commit()
            messagebox.showinfo("Успешно", "Холодильник добавлен!")
            show_fridges(frame)
        except psycopg2.Error as e:
            db_connection.rollback()
            messagebox.showerror("Ошибка", f"Ошибка при добавлении холодильника: {e}")

        tk.Button(frame, text="Добавить", font=("Arial", 12), command=add_fridge_action).pack(pady=10)
        tk.Button(frame, text="Назад", font=("Arial", 12), command=lambda: show_fridges(frame)).pack(pady=5)

# Просмотр данных пользователя
def show_user_data(frame):
    clear_window(frame)

    try:
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT username, login, height, weight, sex, age, email
            FROM public.app_users
            WHERE user_id = %s
        """, (current_user_id,))
        user_data = cursor.fetchone()

        if user_data:
            fields = ["Имя", "Логин", "Рост", "Вес", "Пол", "Возраст", "Почта"]
            for field, value in zip(fields, user_data):
                tk.Label(frame, text=f"{field}: {value if value else 'Не указано'}", font=("Arial", 12)).pack(anchor="w", padx=20, pady=2)

            tk.Button(frame, text="Изменить данные", font=("Arial", 12), command=lambda: edit_user_data(frame)).pack(pady=10)

        tk.Button(frame, text="Назад", font=("Arial", 12), command=lambda: show_user_menu(frame)).pack(pady=10)

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить данные пользователя: {e}")

# Изменение данных пользователя
def edit_user_data(frame):
    clear_window(frame)

    tk.Label(frame, text="Измените данные (оставьте поле пустым, чтобы не изменять):", font=("Arial", 12)).pack(pady=10)

    fields = ["Имя", "Рост", "Вес", "Пол", "Возраст"]
    entries = {}
    for field in fields:
        tk.Label(frame, text=field, font=("Arial", 12)).pack(anchor="w", padx=20)
        entry = tk.Entry(frame, font=("Arial", 12))
        entry.pack(pady=5)
        entries[field] = entry

    def save_user_data():
        updates = {}
        for field, entry in entries.items():
            value = entry.get().strip()
            if value:
                updates[field] = value

        if updates:
            try:
                cursor = db_connection.cursor()
                if "Имя" in updates:
                    cursor.execute("UPDATE public.app_users SET username = %s WHERE user_id = %s", (updates["Имя"], current_user_id))
                if "Рост" in updates:
                    cursor.execute("UPDATE public.app_users SET height = %s WHERE user_id = %s", (updates["Рост"], current_user_id))
                if "Вес" in updates:
                    cursor.execute("UPDATE public.app_users SET weight = %s WHERE user_id = %s", (updates["Вес"], current_user_id))
                if "Пол" in updates:
                    cursor.execute("UPDATE public.app_users SET sex = %s WHERE user_id = %s", (updates["Пол"], current_user_id))
                if "Возраст" in updates:
                    cursor.execute("UPDATE public.app_users SET age = %s WHERE user_id = %s", (updates["Возраст"], current_user_id))
                db_connection.commit()
                messagebox.showinfo("Успешно", "Данные обновлены!")
                show_user_data(frame)
            except Exception as e:
                db_connection.rollback()
                messagebox.showerror("Ошибка", f"Не удалось обновить данные: {e}")

    tk.Button(frame, text="Сохранить изменения", font=("Arial", 12), command=save_user_data).pack(pady=10)
    tk.Button(frame, text="Назад", font=("Arial", 12), command=lambda: show_user_data(frame)).pack(pady=5)

# Регистрация
def register_action(name, login, password, confirm_password, height, weight, sex, age, email, frame):
    password_error = validate_password(password)
    if password_error:
        messagebox.showerror("Ошибка", password_error)
        return

    if password != confirm_password:
        messagebox.showerror("Ошибка", "Пароли не совпадают!")
        return

    if not name or not login or not password or not email:
        messagebox.showerror("Ошибка", "Обязательные поля должны быть заполнены!")
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute("BEGIN")
        cursor.execute("""
            CALL public.add_new_user(
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (name, login, password, email, height or None, weight or None, sex or None, age or None))
        db_connection.commit()
        messagebox.showinfo("Успешно", "Регистрация прошла успешно!")
        return_to_main(frame)
    except psycopg2.Error as e:
        db_connection.rollback()
        messagebox.showerror("Ошибка", f"Ошибка при регистрации: {e}")

# Форма входа
def show_login_form(frame):
    clear_window(frame)

    tk.Label(frame, text="Логин", font=("Arial", 12)).pack(pady=5)
    login_entry = tk.Entry(frame, font=("Arial", 12))
    login_entry.pack()

    tk.Label(frame, text="Пароль", font=("Arial", 12)).pack(pady=5)
    password_entry = tk.Entry(frame, font=("Arial", 12), show="*")
    password_entry.pack()

    tk.Button(frame, text="Войти", font=("Arial", 12),
              command=lambda: login_action(login_entry.get(), password_entry.get(), frame)).pack(pady=10)

    tk.Button(frame, text="Назад", font=("Arial", 12), command=lambda: return_to_main(frame)).pack(pady=5)

# Форма регистрации
def show_register_form(frame):
    clear_window(frame)

    tk.Label(frame, text="Имя", font=("Arial", 12)).pack(pady=5)
    name_entry = tk.Entry(frame, font=("Arial", 12))
    name_entry.pack()

    tk.Label(frame, text="Логин", font=("Arial", 12)).pack(pady=5)
    login_entry = tk.Entry(frame, font=("Arial", 12))
    login_entry.pack()

    tk.Label(frame, text="Пароль", font=("Arial", 12)).pack(pady=5)
    password_entry = tk.Entry(frame, font=("Arial", 12), show="*")
    password_entry.pack()

    tk.Label(frame, text="Повтор пароля", font=("Arial", 12)).pack(pady=5)
    confirm_password_entry = tk.Entry(frame, font=("Arial", 12), show="*")
    confirm_password_entry.pack()

    tk.Label(frame, text="Рост (см) (необязательно)", font=("Arial", 12)).pack(pady=5)
    height_entry = tk.Entry(frame, font=("Arial", 12))
    height_entry.pack()

    tk.Label(frame, text="Вес (кг) (необязательно)", font=("Arial", 12)).pack(pady=5)
    weight_entry = tk.Entry(frame, font=("Arial", 12))
    weight_entry.pack()

    tk.Label(frame, text="Пол (М/Ж) (необязательно)", font=("Arial", 12)).pack(pady=5)
    sex_entry = tk.Entry(frame, font=("Arial", 12))
    sex_entry.pack()

    tk.Label(frame, text="Возраст (необязательно)", font=("Arial", 12)).pack(pady=5)
    age_entry = tk.Entry(frame, font=("Arial", 12))
    age_entry.pack()

    tk.Label(frame, text="Почта", font=("Arial", 12)).pack(pady=5)
    email_entry = tk.Entry(frame, font=("Arial", 12))
    email_entry.pack()

    tk.Button(frame, text="Зарегистрироваться", font=("Arial", 12),
              command=lambda: register_action(name_entry.get(), login_entry.get(), password_entry.get(),
                                              confirm_password_entry.get(), height_entry.get(),
                                              weight_entry.get(), sex_entry.get(),
                                              age_entry.get(), email_entry.get(), frame)).pack(pady=10)

    tk.Button(frame, text="Назад", font=("Arial", 12), command=lambda: return_to_main(frame)).pack(pady=5)

# Главный экран
def main_screen(frame):
    tk.Label(frame, text="Добро пожаловать в My Fridge App!", font=("Arial", 14)).pack(pady=20)

    tk.Button(frame, text="Вход", font=("Arial", 12), command=lambda: show_login_form(frame)).pack(pady=5)
    tk.Button(frame, text="Регистрация", font=("Arial", 12), command=lambda: show_register_form(frame)).pack(pady=5)

# Главное приложение
def main_app():
    root = tk.Tk()
    root.title("My Fridge App")
    root.geometry("400x600")
    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True)
    main_screen(frame)
    root.mainloop()

if __name__ == "__main__":
    if db_connection:
        main_app()