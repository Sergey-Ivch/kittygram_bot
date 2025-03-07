from telegram import Update
import requests
import logging
from telegram.ext import Updater, CallbackContext, MessageHandler, CallbackQueryHandler, CommandHandler, Filters
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from typing import List, Dict

updater = Updater(token='7814399961:AAEt7Wwo80daNL2tL07k3GzHuey-_sP97cc')
URL = "https://testhome.pythonanywhere.com/api/cats/"


# Настройка логирования - это важно для продакшена
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__) # Получаем логгер для этого модуля


BREEDS_PER_PAGE = 10

# Константы для текста сообщений
WELCOME_MESSAGE = (
    "Привет! {} 👋\n\n"
    "Я - твой персональный кот-консультант!\n\n"
    "Мечтаешь о пушистом друге, но не знаешь, какая порода кошек подойдет именно тебе? 😻\n\n"
    "Я помогу тебе сделать правильный выбор!\nПросто ответь на несколько простых вопросов"
    " о своем образе жизни и предпочтениях, и я подберу идеального кота для тебя. ✨\n\n"
    "Просто отвечай на мои вопросы, и мы найдем твоего идеального кота! 🐾\n\n"
    'Приступить можете в любой момент, просто нажмите в выпадающем меню на кнопку "Начать"'
)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [['Все породы', 'Полезные статьи об уходе'], ['Начать']], resize_keyboard=True
)

# Определяем константы - выносим их за функцию, чтобы не вычислять каждый раз
LITTLE_MIN_WEIGHT = 2.5
LITTLE_MAX_WEIGHT = 4.0
AVERAGE_MIN_WEIGHT = 4.0
AVERAGE_MAX_WEIGHT = 5.5
LARGE_MIN_WEIGHT = 5.5
LARGE_MAX_WEIGHT = 9.0

ST_MIN_LIFE_EXPECTANCY = 0.0
ST_MAX_LIFE_EXPECTANCY = 13.75
DO_MIN_LIFE_EXPECTANCY = 13.75
DO_MAX_LIFE_EXPECTANCY = 20.0

QUESTIONS: Dict[int, Dict[str, any]] = {
    1: {
        "text": "Есть ли у вас аллергия на кошек, или кто-то в семье аллергик?",
        "answers": ["1.Нет аллергии", "2.Есть аллергия"],
        "callback_values": {"no_allergic": "Нет аллергии", "allergic": "Аллергия"},
    },
    2: {
        "text": "В каких условиях будет жить ваша кошка?",
        "answers": ["1.Только в помещении", "2.Ограниченный доступ на улицу", "3.Свободный доступ на улицу"],
        "callback_values": {"Indoor_only": "Помещение", "Limited_access": "Ограниченный", "Free_access": "Свободный"},
    },
    3: {
        "text": "В каком населенном пункте вы проживаете?",
        "answers": ["1.Город", "2.Пригород", "3.Деревня"],
        "callback_values": {"City": "Город", "Suburb": "Пригород", "Village": "Деревня"},
    },
    4: {
        "text": "Сколько времени вы готовы уделять уходу за шерстью кота?",
        "answers": ["1.Минимум (редкое расчесывание, минимум ухода)", "2.Много (ежедневное расчесывание, профессиональный груминг)"],
        "callback_values": {"min_grooming": "Базовый", "med_grooming": "Регулярный"},
    },
    5: {
        "text": "Насколько активного кота вы хотите?",
        "answers": ["1.Активного (любит играть, много двигается)", "2.Спокойного (предпочитает отдыхать)"],
        "callback_values": {"very_active": "Активный", "calm": "Спокойный"},
    },
    6: {
        "text": "Какой вес кота вы бы хотели?",
        "answers": ["1.Маленький (2.5 - 4.0 кг)", "2.Средний (4.0 - 5.5 кг)", "3.Крупный (5.5 - 9.0 кг)"],
        "callback_values": {"Little": "Little", "Average": "Average", "Large": "Large"},
    },
    7: {
        "text": "Какую продолжительность жизни кота вы бы хотели?",
        "answers": ["1.Стандартная", "2.Долгожитель"],
        "callback_values": {"10": "Ten", "10_15": "Ten-five"},
    },
}

FORMATTED_VALUES: List[str] = []

def fetch_cat_data(url: str) -> List[Dict]:
    """
    Получает данные о кошках из API.

    Args:
        url: URL API.

    Returns:
        Список словарей с данными о кошках.  Возвращает пустой список в случае ошибки.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {e}")
        return []  #  Возвращаем пустой список при ошибке, чтобы обработать ее дальше


def filter_cats(cat_data: List[Dict], formatted_values: List[str]) -> List[Dict]:
    """
    Фильтрует данные о кошках на основе заданных критериев.

    Args:
        cat_data: Список словарей с данными о кошках.
        formatted_values: Список отформатированных значений для фильтрации (care, activity, size, life_expectancy).

    Returns:
        Список словарей с отфильтрованными данными о кошках.
    """

    care = formatted_values[3]
    activity = formatted_values[4]
    size = formatted_values[5]
    life_expectancy_group = formatted_values[6]

    # Определяем диапазоны значений для веса кошки
    if size == "Little":
        min_value = LITTLE_MIN_WEIGHT
        max_value = LITTLE_MAX_WEIGHT
    elif size == "Average":
        min_value = AVERAGE_MIN_WEIGHT
        max_value = AVERAGE_MAX_WEIGHT
    else:  # Implicitly handles "Large" or any other value
        min_value = LARGE_MIN_WEIGHT
        max_value = LARGE_MAX_WEIGHT

    # Определяем диапазоны значений для продолжительности жизни
    if life_expectancy_group == 'Ten':
        mini_value = ST_MIN_LIFE_EXPECTANCY
        maxi_value = ST_MAX_LIFE_EXPECTANCY
    elif life_expectancy_group == 'Ten-five':
        mini_value = DO_MIN_LIFE_EXPECTANCY
        maxi_value = DO_MAX_LIFE_EXPECTANCY
    else:
        logger.warning(f"Неизвестная группа продолжительности жизни: {life_expectancy_group}")
        return [] # Возвращаем пустой список, если группа невалидна

    filtered_cats = []
    for item in cat_data:
        try:
            weight = float(item.get("weight_of_the_cat", 0.0))  # Default to 0.0 if missing
            life_expectancy = float(item.get("life_expectancy", 0.0)) # Default to 0.0 if missing

            if (
                item.get("care") == care
                and item.get("activity") == activity
                and min_value <= weight <= max_value
                and mini_value <= life_expectancy <= maxi_value
            ):
                filtered_cats.append(item)
        except (ValueError, TypeError) as e:
            logger.warning(f"Ошибка при обработке данных кошки (ID: {item.get('id', 'N/A')}): {e}")

    return filtered_cats


def new_cat(update: Update, context: CallbackContext, formatted_values: List[str]) -> None:
    """
    Обработчик команды /new_cat.  Получает данные о кошках, фильтрует их и отправляет пользователю список подходящих пород.

    Args:
        update: Объект Update от Telegram.
        context: Объект CallbackContext от telegram.ext.
        charlie_list: Список, в который будут добавлены отфильтрованные кошки (замена на возвращаемое значение).
        URL: URL API.
        formatted_values: Список отформатированных значений для фильтрации.
    """

    cat_data = fetch_cat_data(URL)  #  Получаем данные о кошках

    if not cat_data:
        update.callback_query.message.reply_text("Извините, не удалось получить данные о кошках. Попробуйте позже.")
        return


    filtered_cats = filter_cats(cat_data, formatted_values) # Фильтруем кошек

    if not filtered_cats:
        update.callback_query.message.reply_text(
            "К сожалению, не найдено кошек, соответствующих вашим критериям. Попробуйте изменить параметры поиска."
        )
        return

    #  Создаем клавиатуру с названиями пород
    inline_keyboard = [
        [InlineKeyboardButton(element['breed'], callback_data=f"breed_{element['id']}")]
        for element in filtered_cats
    ]

    #  Отправляем сообщение пользователю
    update.callback_query.message.reply_text(
        'Отлично!\n\n Основываясь на ваших ответах, я подобрал для вас породы кошек, которые,'
        'скорее всего, вам понравятся. Я учел ваши пожелания к активности, размеру и другим важным характеристикам.\n\n'
        'Нажмите на название породы, чтобы увидеть подробное описание!',
        reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )


def wake_up(update: Update, context: CallbackContext) -> None:
    """
    Обработчик команды /start. Приветствует пользователя и показывает главное меню.
    """
    chat = update.effective_chat
    name = update.message.chat.first_name
    context.bot.send_message(
        chat_id=chat.id, text=WELCOME_MESSAGE.format(name), reply_markup=MAIN_KEYBOARD
    )


def start_questionnaire(update: Update, context: CallbackContext) -> None:
     """
     Обработчик команды "Начать". Запускает опрос.
     """
     # Clear previous answers before starting a new questionnaire
     FORMATTED_VALUES.clear()  # Clear formatted values when starting
     Questionnaire(update, context, 1)  # Start with the first question


def Questionnaire(update: Update, context: CallbackContext, index: int) -> None:
    """
    Задает вопрос пользователю.
    """
    question = QUESTIONS[index]
    chat = update.effective_chat
    inline_keyboard = [
        [InlineKeyboardButton(answer, callback_data=f"question_{index}_{values}")]
        for answer, values in zip(question["answers"], question["callback_values"].keys())
    ]  # Access keys instead of values directly

    # Отправляем сообщение с клавиатурой
    if update.message:
        context.bot.send_message(chat_id=chat.id, text='Отлично! Начнем!')
        update.message.reply_text(question["text"], reply_markup=InlineKeyboardMarkup(inline_keyboard))
    elif update.callback_query:
        update.callback_query.message.reply_text(question["text"], reply_markup=InlineKeyboardMarkup(inline_keyboard))


def process_button(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает ответ пользователя и задает следующий вопрос или завершает опрос.
    """
    query = update.callback_query
    query.answer()

    data = query.data

    if data.startswith('page:'):
        page = int(data.split(':')[1])
        All_breeds(update, context, page)
        logger.warning("Функция say_his не определена.")
    elif data.startswith('question'):
        answer(update, context) 
        logger.warning("Функция answer не определена.")
    elif data.startswith('breed'):
        answered(update, context) 
        logger.warning("Функция answered не определена.")



def show_breed_info(update: Update, context: CallbackContext, breed_id: int):
    """
    Отображает подробную информацию о выбранной породе кошек.
    """
    chat = update.effective_chat
    query = update.callback_query
    query.answer()

    try:
        response = requests.get(URL).json()  # Get all cat data

        # Ensure breed_id is valid
        if breed_id < 1 or breed_id > len(response):
            logger.error(f"Invalid breed_id: {breed_id}")
            query.message.reply_text("Извините, информация о данной породе недоступна.")
            return
        cat_data = response[breed_id - 1] # Access directly by index
        caption = (
            "1. Основная информация:\n"
            f"    Название породы: <b>{cat_data.get('breed')}</b>\n"
            f"    Средняя продолжительность жизни: <b>{cat_data.get('life_expectancy')} лет</b>.\n\n\n"
            "2. Характеристики породы:\n"
            f"    Размер: <b>{cat_data.get('weight_of_the_cat')} кг</b>\n"
            f"    Активность: <b>{cat_data.get('activity')}</b>\n"
            f"    Шерсть: <b>{cat_data.get('Wool')}</b>\n"
            f"    Линька: <b>{cat_data.get('Molting')}</b>\n"
            f"    Отношение к детям: <b>{cat_data.get('Attitude_towards_children')}</b>\n"
            f"    Отношение к другим животным: <b>{cat_data.get('Attitude_towards_other_animals')}</b>\n"
            f"    Уровень интеллекта: <b>{cat_data.get('The_level_of_intelligence')}</b>\n"
            f"    Потребность во внимании: <b>{cat_data.get('The_need_for_attention')}</b>\n\n\n"
            "3. Уход и содержание:\n"
            f"    Особенности ухода за шерстью: <b>{cat_data.get('care')}</b>\n"
            f"    Особенности питания: <b>{cat_data.get('Nutrition_features')}</b>\n"
        )

        context.bot.send_photo(
            chat_id=chat.id, photo=cat_data.get('image'), caption=caption, parse_mode='HTML'
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching cat {e}")
        query.message.reply_text("Извините, не удалось получить информацию о породе. Попробуйте позже.")
    except Exception as e:
        logger.exception(f"Unexpected error in show_breed_info: {e}")
        query.message.reply_text("Произошла ошибка при обработке запроса. Попробуйте позже.")
    finally:
        query.edit_message_reply_markup(reply_markup=None)  # Remove inline keyboard


def answer(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор ответа на вопрос анкеты.
    """
    global FORMATTED_VALUES  # Access the global variable
    query = update.callback_query
    query.answer()

    try:
        _, index, answer = query.data.split("_", 2)
        index = int(index)

        if index not in QUESTIONS:
            logger.error(f"Invalid qid: {index}")
            query.message.reply_text("Произошла ошибка. Пожалуйста, начните опрос заново.")
            return

        question = QUESTIONS[index]
        formatted_answers = []
        for answer_key, answer_text in zip(question["callback_values"].keys(), question["answers"]):
            if answer_key == answer:
                formatted_line = answer_text + " ✅ \n"  # Mark selected answer
                formatted_value = question["callback_values"][answer_key]
                # Append the value, not the key
                FORMATTED_VALUES.append(formatted_value)
            else:
                formatted_line = answer_text + "\n"

            formatted_answers.append(formatted_line)
        logger.info(f"Current answers: {FORMATTED_VALUES}")  # Log the answers
        formatted_text = "".join(formatted_answers)
        query.edit_message_text(text=f"{question['text']}\n\n{formatted_text}", reply_markup=None)

        if index < len(QUESTIONS):
            Questionnaire(update, context, index + 1)  # Ask the next question
        else:
            new_cat(update, context, FORMATTED_VALUES)

    except Exception as e:
        logger.exception(f"Error processing answer: {e}")
        query.message.reply_text("Произошла ошибка при обработке ответа. Пожалуйста, попробуйте еще раз.")


def answered(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает выбор породы кошки и отображает информацию о ней.
    """

    query = update.callback_query
    query.answer()

    try:
        _, breed_id = query.data.split("_", 1)
        breed_id = int(breed_id)

        show_breed_info(update, context, breed_id)
    except ValueError:
        logger.error("Invalid breed_id format.")
        query.message.reply_text("Произошла ошибка. Неверный формат ID породы.")
    except Exception as e:
        logger.exception(f"Error processing breed selection: {e}")
        query.message.reply_text("Произошла ошибка при отображении информации о породе. Попробуйте позже.")


def fetch_cat_breeds() -> List[dict]:
    """
    Извлекает данные о породе кошек из API, обрабатывая возможные ошибки.
    """
    try:
        response = requests.get(URL)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching cat breeds from API: {e}")
        return []

def All_breeds(update: Update, context: CallbackContext, page: int = 0) -> None:
    """
    Отображает постраничный список пород кошек.
    """
    cat_breeds = fetch_cat_breeds()

    if not cat_breeds:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Извините, не удалось получить список пород кошек. Попробуйте позже."
        )
        return

    chat_id = update.effective_chat.id
    start_index = page * BREEDS_PER_PAGE
    end_index = start_index + BREEDS_PER_PAGE
    breeds_on_page = cat_breeds[start_index:end_index]

    inline_keyboard = []
    for element in breeds_on_page:
        inline_keyboard.append([InlineKeyboardButton(element['breed'], callback_data=f"breed_{element['id']}")])

    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page:{page - 1}"))
    if end_index < len(cat_breeds):
        navigation_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data=f"page:{page + 1}"))

    if navigation_buttons:
        inline_keyboard.append(navigation_buttons)

    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    total_pages = (len(cat_breeds) + BREEDS_PER_PAGE - 1) // BREEDS_PER_PAGE  # Calculate total pages

    text = f"Выберите породу кошки (страница {page + 1} из {total_pages}):"

    try:
        if update.callback_query:
            update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            context.bot.send_message(chat_id, text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending breeds list message: {e}")



def Useful_articles(update: Update, context: CallbackContext) -> None:
    """
    Отображает полезные статьи по уходу за кошками.
    """

    inline_keyboard = [
        [InlineKeyboardButton('Уход за кошками', url="https://www.purinaone.ru/cat/articles/new-owner-tips/kak-uhazhivat-za-koshkoj")],
        [InlineKeyboardButton('Кормление', url="https://www.purinaone.ru/cat/articles/nutrition")],
        [InlineKeyboardButton('Здоровье', url="https://www.proplan.ru/vet-diets/article/chto-nuzhno-znat-o-zdorov-ie-koshki-samostoiatiel-noie-nabliudieniie-i-profilaktichieskii-osmotr")],
        [InlineKeyboardButton('Воспитание', url="https://www.purinaone.ru/cat/articles/new-owner-tips/kak-vospitat-kotenka")]
    ]

    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    try:
        update.message.reply_text(
            text='Забота о кошке – это большая ответственность.\n\nМы собрали для тебя полезные статьи, которые помогут тебе обеспечить ей счастливую и здоровую жизнь:',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error sending care articles message: {e}")


# Define the error handler
def error_handler(update: Update, context: CallbackContext):
    """
    Регистрируйте ошибки, вызванные обновлениями.
    """
    logger.error(f"Update {update} caused error {context.error}")


def main():
    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Начать"), start_questionnaire))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Все породы"), All_breeds))
    updater.dispatcher.add_handler(MessageHandler(Filters.text("Полезные статьи об уходе"), Useful_articles))
    updater.dispatcher.add_handler(CallbackQueryHandler(process_button))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main() 