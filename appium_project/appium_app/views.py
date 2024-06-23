from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .forms import DeviceForm
import threading
from io import StringIO
from appium import webdriver
from selenium.webdriver.common.by import By
from appium.webdriver.common.touch_action import TouchAction
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from appium.options.common.base import AppiumOptions
import subprocess
import re

class AppiumThread(threading.Thread):
    def __init__(self, device_data, output):
        self.device_data = device_data
        self.output = output
        super().__init__()

    def run(self):
        run_appium_script(self.device_data, self.output)

def run_appium_script(device_data, output):
    desired_caps = {
        "appPackage": "com.mygate.user",
        "appActivity": ".modules.shared.SplashActivity",
        "noReset": True
    }
    desired_caps.update(device_data)

    options = AppiumOptions()
    for key, value in desired_caps.items():
        options.set_capability(key, value)

    print("Opening MyGate App....")
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)

    time.sleep(2)

    def scroll_down():
        size = driver.get_window_size()
        start_x = size['width'] // 2
        start_y = size['height'] * 4.76535 // 5.76535
        end_y = size['height'] // 9

        # Perform scroll
        TouchAction(driver).press(x=start_x, y=start_y).wait(1000).move_to(x=start_x, y=end_y).release().perform()

    wait = WebDriverWait(driver, 20)

    print("Navigating to Community Section....")

    driver.find_element(By.ID, "com.mygate.user:id/navigation_bar_item_small_label_view").click()
    time.sleep(2)

    print("Navigating to Daily Help Section....")
    driver.find_element(By.XPATH, '(//android.view.ViewGroup[@resource-id="com.mygate.user:id/container_item"])[5]').click()
    time.sleep(2)



    maid_data = {'name': [], 'category': [], 'phone': [], 'freetime': []}
    society_string= "Demo"
    required_section = device_data['profession']

    sections = driver.find_elements(By.ID, "com.mygate.user:id/typeName")
    
    counter=0
    for section in sections:
        section_name = section.text
        counter=counter+1
        if section_name == required_section:
            print(f'Found & Navigating to section {required_section}....')
            count=int(driver.find_elements(By.XPATH, '//android.widget.TextView[@resource-id="com.mygate.user:id/count"]')[counter-1].text)
            section.click()
            time.sleep(4)
            break
    else:
        driver.quit()
        output.write("Section not found.\n")
        return

    size = len(driver.find_elements(By.XPATH, '//androidx.recyclerview.widget.RecyclerView[@resource-id="com.mygate.user:id/helpListView"]/android.widget.FrameLayout[*]/android.view.ViewGroup'))

    x = (int(count/size)) * size
    x1 = count - x


    def scrape_maids():
        time.sleep(3)
        for index in range(count):
            if index >= x:
                i = (index % size) + (size - x1)
            else:
                i = (index % size)

            if (index != 0) and (index % size == 0):
                scroll_down()

            time.sleep(2)

            print(f'Processing {index+1}/{count}')
            Inside_maid = driver.find_elements(By.XPATH, f'//androidx.recyclerview.widget.RecyclerView[@resource-id="com.mygate.user:id/helpListView"]/android.widget.FrameLayout[{i+1}]/android.view.ViewGroup')
            Inside_maid[0].click()
            time.sleep(2)
            name = wait.until(EC.presence_of_element_located((By.XPATH, '//android.widget.TextView[@resource-id="com.mygate.user:id/user_name"]'))).text
            phone = wait.until(EC.presence_of_element_located((By.XPATH, '//android.widget.TextView[@resource-id="com.mygate.user:id/helper_contact_no"]'))).text
            try:
                freetime = driver.find_element(By.XPATH, '//android.widget.TextView[starts-with(@resource-id, "com.mygate.user:id/slot") and contains(@resource-id, "_text")]').text
            except:
                freetime = 'NA'
            maid_data['name'].append(name)
            maid_data['category'].append(required_section.upper())
            maid_data['phone'].append(phone)
            maid_data['freetime'].append(freetime)
            driver.find_element(By.ACCESSIBILITY_ID, "Back").click()
            time.sleep(2)
            output.write(f"Scraped: {name}, {phone}, {freetime}\n")

    scrape_maids()

    global fileName
    fileName = f'{society_string}_{required_section}_mygate.csv'

    df = pd.DataFrame(maid_data)
    csv_data = df.to_csv(index=False, header=True)
    output.write(csv_data)

    driver.quit()

def home(request):
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            device_data = {
                "platformName": form.cleaned_data['platform_name'],
                "platformVersion": form.cleaned_data['platform_version'],
                "deviceName": form.cleaned_data['device_name'],
                "profession": form.cleaned_data['profession']
            }
            output = StringIO()
            thread = AppiumThread(device_data, output)
            thread.start()
            thread.join()
            response = HttpResponse(output.getvalue(), content_type='csv')
            response['Content-Disposition'] = f'attachment; filename={fileName}'
            return response
    else:
        form = DeviceForm()

    return render(request, 'appium_app/home.html', {'form': form})

def get_device_id(request):
    try:
        # Run the adb devices command
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, shell=True)
        
        if result.returncode != 0:
            return JsonResponse({'error': result.stderr}, status=500)
        
        # Extract device ID using regular expression
        match = re.search(r'(\w+)\tdevice', result.stdout)
        if match:
            device_id = match.group(1)
            return JsonResponse({'device_id': device_id})
        else:
            return JsonResponse({'error': 'No device found'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_platform_version(request):
    try:
        # Run the adb devices command
        result = subprocess.run(['adb', 'shell', 'getprop', 'ro.build.version.release'], capture_output=True, text=True, shell=True)

        if result.returncode != 0:
            return JsonResponse({'error': result.stderr}, status=500)
        else:
            return JsonResponse({'platform_version' : result.stdout})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_platform_name(request):
    try:
        # Run the adb devices command
        result = subprocess.run(['adb', 'shell', 'getprop', 'net.bt.name'], capture_output=True, text=True, shell=True)

        if result.returncode != 0:
            return JsonResponse({'error': result.stderr}, status=500)
        else:
            return JsonResponse({'platform_name' : result.stdout})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
