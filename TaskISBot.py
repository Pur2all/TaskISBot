import datetime
import multiprocessing as mp
import os
import telebot
import time
import requests

from bs4 import BeautifulSoup
from typing import List


TOKEN = os.environ["TOKEN_BOT"]
TASKS_FILENAME = "tasks.txt"
CHATID_FILENAME = "chatIds.txt"


session = requests.Session()
bot = telebot.TeleBot(TOKEN)


def get_tasks_names() -> List[str]:
    """
        This function get all tasks names and return they as a list of string
    """
    is_url = "http://elearning.informatica.unisa.it/el-platform/course/view.php?id=464"
    response = session.get(is_url)
    site_dom = BeautifulSoup(response.content, "html.parser")
    task_li_element = site_dom.find(id="section-2")
    tasks_list = task_li_element.find_all("li", {"class": "activity assign modtype_assign"})
    tasks_names = []
    for task in tasks_list:
        task_span = task.find("span", {"class": "instancename"})
        tasks_names.append(task_span.text)

    return tasks_names


def do_login(username: str = None, password: str = None) -> str:
    """
        This function perform a login action on e-leraning platform
    """
    if username is None or password is None:
        return "E zumbat"
    
    login_url = "http://elearning.informatica.unisa.it/el-platform/login/index.php"
    response = session.get(login_url)
    site_dom = BeautifulSoup(response.content, "html.parser")
    login_form = site_dom.find(id="guestlogin")
    data = {
        "logintoken": login_form.input["value"],
        "username": username,
        "password": password
    }
    response = session.post(login_url, data=data)

    print("Valore del login eseguito: ", os.environ["NAME_SURNAME"] in response.content.__str__())


def check_if_there_is_new_task() -> str:
    """
        This function check if there are new tasks 
    """
    tasks_names = get_tasks_names()

    task_file = open(TASKS_FILENAME, "r")
    tasks_names_read_from_file = task_file.readlines()
    task_file.close()

    len_task_names = len(tasks_names)
    len_task_names_file = len(tasks_names_read_from_file)

    if len_task_names > len_task_names_file:

        new_tasks = []
        for i in range(len_task_names_file, len_task_names):
            new_tasks.append(tasks_names[i])

        message = "Ci sono nuove task da svolgere: "
        for task in new_tasks:
            message += "\n\t- " + task

        return message
    
    return None
        

def initialize_tasks_file():
    """
        This function read the current tasks and save them in a file
    """
    tasks_names = get_tasks_names()
    
    tasks_file = open(TASKS_FILENAME, "w")
    tasks_file.writelines("\n".join(tasks_names))
    tasks_file.close()


def do_logout():
    """
        This function perform a logout action on e-leraning platform
    """
    logout_url = "http://elearning.informatica.unisa.it/el-platform/login/logout.php"
    response = session.get(logout_url)
    site_dom = BeautifulSoup(response.content, "html.parser")
    form = site_dom.find("form", {"action": logout_url})
    sesskey = form.input["value"]
    response = session.post(logout_url, data={"sesskey": sesskey})

    print("Valore di logout eseguito: ", "Non sei collegato" in response.content.__str__())


def save_chat_id(chatId):
    """
        This function save chat ids in a file to save who to send message
    """
    chat_id_file = open(CHATID_FILENAME, "a")
    chat_id_file.write(str(chatId) + "\n")
    chat_id_file.close()


def check_tasks(login_function, args):
    """
        This function check if there are new tasks every 3 hours, except from midnight to 10 AM
    """
    while True:
        current = datetime.datetime.now()
        current_time = current.time()
        midnight = datetime.datetime(year=current.year, month=current.month, day=current.day, hour=00, minute=00, second=00).time()
        tenAM = datetime.datetime(year=current.year, month=current.month, day=current.day, hour=10, minute=00, second=00).time()
        if not midnight < current_time < tenAM:
            login_function(*args)
            tasks_message = check_if_there_is_new_task()
            do_logout()

            if tasks_message:
                while not os.path.exists(CHATID_FILENAME):
                    time.sleep(1)
                chat_id_file = open(CHATID_FILENAME, "r")
                chat_ids = chat_id_file.readlines()
                chat_id_file.close()
                for chatId in chat_ids:
                    bot.send_message(chatId.replace("\n", ""), tasks_message)

        time.sleep(60*60*3)


@bot.message_handler(commands=["start"])
def check_messages(message):
    bot.send_message(message.chat.id, "Da adesso in poi riceverai le notifiche ogni qualvolta verrà caricata una task!")
    save_chat_id(message.chat.id)


@bot.message_handler(func=lambda message: message != "/start")
def generic_answer(message):
    bot.send_message(message.chat.id, "Comando non riconosciuto")


username, password = os.environ["USERNAME"], os.environ["PASSWORD"]
do_login(username=username, password=password)
initialize_tasks_file()
do_logout()
check_tasks_process = mp.Process(name="Check Tasks", target=check_tasks, args=(do_login, [username, password]))
check_tasks_process.start()