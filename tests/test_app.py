#!/usr/bin/env python
import time

from selenium.webdriver.common.by import By


def test_empa_molecules_app_take_screenshot(selenium, url):
    selenium.get(
        url("http://localhost:8100/apps/apps/empa-molecules/spin_calculation.ipynb")
    )
    selenium.set_window_size(1920, 985)
    time.sleep(10)
    selenium.find_element(By.ID, "ipython-main-app")
    selenium.find_element(By.ID, "notebook-container")
    selenium.find_element(By.CLASS_NAME, "jupyter-widgets-view")
    selenium.get_screenshot_as_file("screenshots/empa-molecules-app.png")
