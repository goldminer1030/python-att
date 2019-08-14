import requests
import base64
import os
import time
from selenium import webdriver
from PIL import Image, ImageChops
from requests_toolbelt import MultipartEncoder


CAPTCHA_CHECK_URL = "https://www.att.com/prepaid/activations/services/resources/acceptance/captcha/isCaptchaNeeded"
CAPTCHA_IMAGE = "captcha.png"
API_PREFIX = "http://azcaptcha.com",
API_IN_URL = "%s/in.php" % API_PREFIX
API_RES_URL = "%s/res.php" % API_PREFIX
API_KEY = ""


def is_captcha_needed():
    r = requests.post(CAPTCHA_CHECK_URL, json={
        "CommonData": {
            "AppName": "PREPAID_ACTIVATION"
        },
        "app": "prepaid"
    }, headers={
        "Content-Type": "application/json",
        "X-Requested-By": "MYATT"
    })

    if r.status_code == 200:
        result = r.json()
        if result['Result']['Status'] == 'SUCCESS':
            return result['isCaptchaNeeded']

    return False


def get_captcha_image(driver):
    # remove captcha image
    os.remove(CAPTCHA_IMAGE)

    # download image/captcha
    element = browser.find_element_by_xpath(
        "//img[contains(@src,'/prepaid/activations/services/resources/acceptance/captcha/getImage?app=prepaid&_ts')]")

    # now that we have the preliminary stuff out of the way time to get that image :D
    location = element.location
    size = element.size
    # saves screenshot of entire page
    driver.save_screenshot(CAPTCHA_IMAGE)

    # uses PIL library to open image in memory
    image = Image.open(CAPTCHA_IMAGE)

    left = location['x']
    top = location['y']
    right = location['x'] + size['width']
    bottom = location['y'] + size['height']

    image = image.crop((left, top, right, bottom))  # defines crop points
    image.save(CAPTCHA_IMAGE)  # saves new cropped image

    with open(CAPTCHA_IMAGE, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def is_empty_captcha():
    captcha_now = Image.open(CAPTCHA_IMAGE)
    captcha_empty = Image.open("empty-captcha.png")
    return ImageChops.difference(captcha_now, captcha_empty).getbbox() is None


def get_captcha_id(base64_captcha_):
    multipart_form_data_object = MultipartEncoder(
        fields={
            'key': API_KEY,
            'method': 'base64',
            'json': '1',
            'body': base64_captcha_
        }
    )

    res = requests.post(API_IN_URL, data=multipart_form_data_object,
                        headers={'Content-Type': multipart_form_data_object.content_type})

    if res.status_code == 200:
        result_object = res.json()
        if result_object['status'] == 1:
            return result_object['request']

    return None


def get_captcha_text_with_id(captcha_id):
    while True:
        res = requests.get(url=API_RES_URL, params={
            'key': API_KEY,
            'id': captcha_id,
            'action': 'get',
            'json': '1'
        })

        if res.status_code == 200:
            result_object = res.json()
            if result_object['status'] == 1:
                return result_object['request']
        time.sleep(5)
    return None


def get_captcha_from_api(base64_captcha_):
    captcha_id = get_captcha_id(base64_captcha_)
    if captcha_id:
        return get_captcha_text_with_id(captcha_id)

    return None


if __name__ == '__main__':
    is_captcha_needed = is_captcha_needed()

    browser = webdriver.Firefox()
    browser.get('https://www.att.com/prepaid/activations/#/activate.html')

    sim_number = browser.find_element_by_id("simnumber")
    imei_number = browser.find_element_by_id("imeinumber")
    service_zip = browser.find_element_by_id("servicezip")
    submit = browser.find_element_by_id("continueBtn")

    sim_number.send_keys("89014102255039698818")
    imei_number.send_keys("359405084715737")
    service_zip.send_keys("90210")

    if is_captcha_needed:
        browser.implicitly_wait(10)

        base64_captcha = get_captcha_image(browser)

        if is_empty_captcha():
            print('captcha is empty. retry again')

            refresh_captcha = browser.find_element_by_xpath("//img[contains(@src,'images/refresh-captcha.png')]")
            refresh_captcha.click()

            browser.implicitly_wait(10)

            base64_captcha = get_captcha_image(browser)

        captcha = get_captcha_from_api(base64_captcha)
        if captcha:
            captcha_input = browser.find_element_by_id("captcha")
            captcha_input.send_keys(captcha)

            submit.click()
            print('Succeed to get captcha --> %s' % captcha)
        else:
            print('Failed to get captcha')

    else:
        submit.click()

    print("--- FINISHED ---")


