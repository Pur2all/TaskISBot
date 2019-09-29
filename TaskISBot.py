import WiccioGramBot as telegram
import requests
import time
import datetime
import multiprocessing as mp
import os
from bs4 import BeautifulSoup
from typing import List

#Telegram Bot token required to perform requests to Telgram Bot API
TOKEN="YOUR BOT TOKEN"
TASKS_FILENAME="tasks.txt"
CHATID_FILENAME="chatIds.txt"


s=requests.Session()


def getTasksNames() -> List[str]:
    """
        This function get all tasks names and return they as a list of string
    """
    isUrl="http://elearning.informatica.unisa.it/el-platform/course/view.php?id=464"
    response=s.get(isUrl)
    siteDOM=BeautifulSoup(response.content, "html.parser")
    taskLiElement=siteDOM.find(id="section-2")
    tasksList=taskLiElement.find_all("li", {"class": "activity assign modtype_assign"})
    tasksNames=[]
    for task in tasksList:
        taskSpan=task.find("span", {"class": "instancename"})
        tasksNames.append(taskSpan.text)

    return tasksNames



def doLogin(username: str=None, password: str=None) -> str:
    """
        This function perform a login action on e-leraning platform
    """
    if username is None or password is None:
        return "E zumbat"
    
    loginUrl="http://elearning.informatica.unisa.it/el-platform/login/index.php"
    response=s.get(loginUrl)
    siteDOM=BeautifulSoup(response.content, "html.parser")
    loginForm=siteDOM.find(id="guestlogin")
    data={
        "logintoken": loginForm.input["value"],
        "username": username,
        "password": password
    }
    response=s.post(loginUrl, data=data)

    print("Valore del login eseguito: ", "NAME SURNAME" in response.content.__str__())



def checkIfThereIsNewTask() -> str:
    """
        This function check if there are new tasks 
    """
    tasksNames=getTasksNames()

    taskFile=open(TASKS_FILENAME, "r")
    tasksNamesReadFromFile=taskFile.readlines()
    taskFile.close()

    lenTaskNames=len(tasksNames)
    lenTaskNamesFile=len(tasksNamesReadFromFile)

    if lenTaskNames>lenTaskNamesFile:

        newTasks=[]
        for i in range(lenTaskNamesFile, lenTaskNames):
            newTasks.append(tasksNames[i])

        message="Ci sono nuove task da svolgere: "
        for task in newTasks:
            message+="\n\t- " + task

        return message
    
    return None
        


def initializeTasksFile():
    """
        This function read the current tasks and save them in a file
    """
    tasksNames=getTasksNames()
    
    tasksFile=open(TASKS_FILENAME, "w")
    tasksFile.writelines("\n".join(tasksNames))
    tasksFile.close()



def doLogout():
    """
        This function perform a logout action on e-leraning platform
    """
    logoutUrl="http://elearning.informatica.unisa.it/el-platform/login/logout.php"
    response=s.get(logoutUrl)
    siteDOM=BeautifulSoup(response.content, "html.parser")
    form=siteDOM.find("form", {"action": logoutUrl})
    sesskey=form.input["value"]
    response=s.post(logoutUrl, data={"sesskey": sesskey})

    print("Valore di logout eseguito: ", "Non sei collegato" in response.content.__str__())



def saveChatId(chatId):
    """
        This function save chat ids in a file to save who to send message
    """
    chatIdFile=open(CHATID_FILENAME, "a")
    chatIdFile.write(str(chatId) + "\n")
    chatIdFile.close()



def checkTasks(loginFunction, args):
    """
        This function check if there are new tasks every 3 hours, except from midnight to 10 AM
    """
    telegram.newBot(TOKEN)
    while True:
        current=datetime.datetime.now()
        currentTime=current.time()
        midnight=datetime.datetime(year=current.year, month=current.month, day=current.day, hour=00, minute=00, second=00).time()
        tenAM=datetime.datetime(year=current.year, month=current.month, day=current.day, hour=10, minute=00, second=00).time()
        if not midnight<currentTime<tenAM:
            loginFunction(*args)
            tasksMessage=checkIfThereIsNewTask()
            doLogout()

            if tasksMessage:
                while not os.path.exists(CHATID_FILENAME):
                    time.sleep(1)
                chatIdFile=open(CHATID_FILENAME, "r")
                chatIds=chatIdFile.readlines()
                chatIdFile.close()
                for chatId in chatIds:
                    telegram.sendMessage(tasksMessage, chatId.replace("\n", ""))

        time.sleep(60*60*3)



def checkMessages():
    """
        This function check if there is a new message from an user every 3 seconds
    """
    telegram.newBot(TOKEN)
    lastUpdateId=None
    while True:
        updates=telegram.getUpdates(lastUpdateId)
        if len(updates["result"])>0:
            lastUpdateId=telegram.getLastUpdateId(updates)+1
            for update in updates["result"]:
                if "message" in update and "text" in update["message"]:
                    messageText=update["message"]["text"]
                    chatId=update["message"]["chat"]["id"]
                    if "/start" in messageText.lower():
                        telegram.sendMessage("Da adesso in poi riceverai le notifiche ogni qualvolta verrà caricata una task!", chatId)
                        saveChatId(chatId)
                    else:
                        telegram.sendMessage("Comando non riconosciuto", chatId)
        time.sleep(3)



if __name__=="__main__":
    username, password="USERNAME", "PASSWORD"
    doLogin(username=username, password=password)
    initializeTasksFile()
    doLogout()
    checkMessagesProcess=mp.Process(name="Check Messages", target=checkMessages)
    checkTasksProcess=mp.Process(name="Check Tasks", target=checkTasks, args=(doLogin, [username, password]))
    checkMessagesProcess.start()
    checkTasksProcess.start()