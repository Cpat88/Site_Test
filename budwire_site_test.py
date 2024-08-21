import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from fpdf import FPDF
from PIL import Image
from io import BytesIO
import glob
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


class BudwireTester:
    def __init__(self, base_url, sender_email, sender_password, recipient_emails):
        self.base_url = base_url
        self.driver = webdriver.Chrome()  # or webdriver.Firefox() if you use Firefox
        self.driver.maximize_window()
        self.results = []
        self.toc_entries = []
        self.pdf = FPDF()
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails  # List of recipient emails

    def clean_up(self):
        image_files = glob.glob("*.png")
        for image_file in image_files:
            try:
                os.remove(image_file)
            except Exception as e:
                print(f"Error deleting file {image_file}: {e}")

    def upload_file(self, field_id, file_path):
        # Find the input element and send the file path
        file_input = self.driver.find_element(By.CSS_SELECTOR, f"input[id='{field_id}']")
        file_input.send_keys(os.path.abspath(file_path))

    def truncate_text(self, text, max_length):
        if len(text) > max_length:
            return text[:max_length - 3] + '...'
        return text

    def take_screenshot(self, name):
        filename = f"{name}.png"

        # Get the dimensions of the webpage
        total_width = self.driver.execute_script("return document.body.scrollWidth")
        total_height = self.driver.execute_script("return document.body.scrollHeight")

        # Get the viewport size
        viewport_width = self.driver.execute_script("return window.innerWidth")
        viewport_height = self.driver.execute_script("return window.innerHeight")

        # Create a blank image to store the final screenshot
        stitched_image = Image.new('RGB', (total_width, total_height))

        # Calculate the number of screenshots needed
        num_screenshots = (total_height // viewport_height) + 1

        for i in range(num_screenshots):
            scroll_y = i * viewport_height

            # Scroll to the position
            self.driver.execute_script(f"window.scrollTo(0, {scroll_y})")
            time.sleep(0.5)  # Adjust sleep time as needed

            # Take a screenshot
            screenshot = self.driver.get_screenshot_as_png()
            screenshot_image = Image.open(BytesIO(screenshot))

            # Calculate the position to paste the screenshot
            paste_position = (0, scroll_y)

            # Adjust the crop height for the last screenshot
            if i == num_screenshots - 1:
                crop_height = total_height - scroll_y
                screenshot_image = screenshot_image.crop(
                    (0, viewport_height - crop_height, total_width, viewport_height)
                )

            # Paste the screenshot into the final image
            stitched_image.paste(screenshot_image, paste_position)

        # Save the final image
        stitched_image.save(filename)

        # Scroll back to the top of the page
        self.driver.execute_script("window.scrollTo(0, 0)")

        return filename


    def load_page(self, url):
        start_time = time.time()
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        load_time = time.time() - start_time
        return load_time

    def register_new_user(self):
        today = datetime.now().strftime("%Y-%m-%d")
        username = f'testuser_{today}'
        email = f'testuser_{today}@example.com'
        password = 'password123'
        company = 'acme_inc'
        first_name = 'cpat_firstname_test'
        last_name = 'cpat_lastname_test'
        address_1 = '123 street'
        address_2 = 'apt 2'
        billing_postcode = 'a1b 234'
        billing_phone = '(555) 555-5555'
        user_url = 'www.budwire.ca'

        load_time = self.load_page(f"{self.base_url}/register")
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "content")))

        self.driver.find_element(By.ID, 'user_login').send_keys(username)
        self.driver.find_element(By.ID, 'user_email').send_keys(email)
        self.driver.find_element(By.ID, 'user_pass').send_keys(password)
        self.driver.find_element(By.ID, 'user_confirm_password').send_keys(password)
        self.driver.find_element(By.ID, 'billing_company').send_keys(company)
        self.driver.find_element(By.ID, 'billing_first_name').send_keys(first_name)
        self.driver.find_element(By.ID, 'billing_last_name').send_keys(last_name)
        self.driver.find_element(By.ID, 'billing_address_1').send_keys(address_1)
        self.driver.find_element(By.ID, 'billing_address_2').send_keys(address_2)
        Select(self.driver.find_element(By.ID, 'billing_state')).select_by_visible_text("Quebec")
        self.driver.find_element(By.ID, 'billing_postcode').send_keys(billing_postcode)
        Select(self.driver.find_element(By.ID, "billing_country")).select_by_visible_text("Canada")
        self.driver.find_element(By.ID, 'billing_phone').send_keys(billing_phone)
        self.driver.find_element(By.ID, 'user_url').send_keys(user_url)

        # Click the "Privacy Policy" checkbox
        privacy_policy_checkbox = self.driver.find_element(By.ID, "privacy_policy_1645042231")
        if not privacy_policy_checkbox.is_selected():
            privacy_policy_checkbox.click()

        terms_conditions_checkbox = self.driver.find_element(By.ID, "privacy_policy_1645042328")
        if not terms_conditions_checkbox.is_selected():
            terms_conditions_checkbox.click()

        self.driver.find_element(By.CLASS_NAME, 'ur-submit-button ').click()
        page_url = self.driver.current_url

        # Wait for the success or error message to appear
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "ur-submit-message-node"))
            )
            success_message_element = self.driver.find_element(By.ID, "ur-submit-message-node")
            success_message_text = success_message_element.text

            success = "User registered. Wait until admin approves your registration." in success_message_text

            # Check for "username already exists" or "email already exists" messages
            if not success:
                error_messages = self.driver.find_elements(By.CSS_SELECTOR, "ul li")
                for message in error_messages:
                    if "Username already exists." in message.text or "Email already exists." in message.text:
                        success = True
                        break

            screenshot = self.take_screenshot('register_new_user')
        except Exception as e:
            print(f"Failed to find the success message. Error: {e}")
            success = False
            screenshot = self.take_screenshot('register_new_user')

        self.results.append({
            'test': 'Register New User',
            'success': success,
            'load_time': load_time,
            'screenshot': screenshot,
            'url': page_url
        })

        return success

    def login_user(self):
        username = 'automatic_testing@budwire.ca'
        password = 'Budwire1234~!'
        load_time = self.load_page(f"{self.base_url}/login")
        self.driver.find_element(By.ID, 'sp-loginform-user-login-v832k7').send_keys(username)
        self.driver.find_element(By.ID, 'sp-user-pass-v832k7').send_keys(password)
        self.driver.find_element(By.ID, 'sp-submit-loginform-v832k7').click()

        try:
            # Wait for the navigation wrap element to appear, indicating successful login
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'site-navigation-wrap'))
            )
            success = True
        except TimeoutException:
            success = False

        page_url = self.driver.current_url
        screenshot = self.take_screenshot('login_user')
        self.results.append({
            'test': 'Login User',
            'success': success,
            'load_time': load_time,
            'screenshot': screenshot,
            'url': page_url
        })
        return success

    def logout_user(self):
        load_time = self.load_page(f"{self.base_url}/logout")
        screenshot = self.take_screenshot('logout_user')
        success = "Logged out" in self.driver.page_source
        page_url = self.driver.current_url
        self.results.append({
            'test': 'Logout User',
            'success': success,
            'load_time': load_time,
            'screenshot': screenshot,
            'url' : page_url
        })
        return success

    def click_menu_item(self, menu_item_id):
        try:
            menu_item = self.driver.find_element(By.ID, menu_item_id)
            menu_item.find_element(By.TAG_NAME, 'a').click()
            return True
        except Exception as e:
            print(f"Failed to click menu item with ID {menu_item_id}. Error: {e}")
            return False

    def test_marketplace(self):
        load_time = self.load_page(f"{self.base_url}")

        # Click on the "Online Marketplace" menu item
        if not self.click_menu_item('menu-item-454'):
            # If clicking failed, return False
            return False

        # Wait for the page to load after clicking the menu item
        WebDriverWait(self.driver, 10).until(EC.url_contains('https://budwire.ca/'))

        # Proceed with the rest of the test
        filters = self.driver.find_elements(By.CLASS_NAME, 'filter')
        for filter_element in filters:
            filter_element.click()
            time.sleep(1)  # wait for the filter to apply
        page_url = self.driver.current_url
        screenshot = self.take_screenshot('marketplace_view')
        success = True  # Additional checks can be added based on the filters
        self.results.append({
            'test': 'Check Marketplace',
            'success': success,
            'load_time': load_time,
            'screenshot': screenshot,
            'url': page_url
        })
        return success

    def request_sample(self):
        load_time = self.load_page(f"{self.base_url}")

        try:
            # Wait until the first 'jet-woo-products__inner-box jet-woo-item-overlay-wrap' element is visible
            product_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".jet-woo-products__inner-box.jet-woo-item-overlay-wrap"))
            )
            # Find the first 'a' tag within the product element and click it
            product_link = product_element.find_element(By.CSS_SELECTOR, ".jet-woo-product-button a")
            product_link.click()

            # Capture the current URL after navigating to the product page
            page_url = self.driver.current_url

        except Exception as e:
            print(f"An error occurred while selecting the product: {e}")
            return False

        try:
            # Wait for the 'Order Sample' button to be present and clickable, then click it
            request_sample_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'budwire_product_order_sample'))
            )
            request_sample_button.click()

            # Wait for the 'Confirm' button in the popup to be present and clickable, then click it
            confirm_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="budwire_sample_order_action"]'))
            )
            confirm_button.click()

            # Wait for the success message to be present
            success_message = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'woocommerce-message'))
            )

            screenshot = self.take_screenshot('request_sample')

            success = "Thank you for your order!" in success_message.text
            self.results.append({
                'test': 'Request Sample',
                'success': success,
                'load_time': load_time,
                'screenshot': screenshot,
                'url': page_url
            })
            return success
        except Exception as e:
            print(f"An error occurred during the sample request: {e}")
            return False

    def create_new_product(self):
        load_time = self.load_page(f"{self.base_url}/dashboard")

        try:
            # Wait until the dashboard is loaded
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "dokan-navigation"))
            )

            # Click on the "Products" link in the side panel
            products_link = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//li[@class='products']/a"))
            )
            products_link.click()

            # Measure the load time for the "Add New Product" page
            start_time = time.time()

            # Click on the "Add New Product" button with specific text
            add_new_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Add new product')]"))
            )
            add_new_button.click()

            # Wait until the "Add New Product" page is fully loaded
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "dokan-product-title-area"))
            )

            end_time = time.time()
            load_time = end_time - start_time

            # Fill in the product information
            product_name = f"Test Product {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.driver.find_element(By.ID, 'post_title').send_keys(product_name)

            # Set the lot number
            lot_number = "TESTLOT123456"  # Example lot number, change as needed
            self.driver.find_element(By.NAME, 'budwire_lot_number').send_keys(lot_number)

            # Click on the "Upload a product cover image" button
            upload_image_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".dokan-feat-image-btn"))
            )
            upload_image_button.click()

            # Wait for the "Media Library" button to be clickable and click it
            media_library_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.ID, "menu-item-browse"))
            )
            media_library_button.click()

            # Wait for the first image in the media library to be clickable and click it
            first_image = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".attachments .attachment:first-child"))
            )
            first_image.click()

            # Confirm the selection
            select_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".media-button-select"))
            )
            select_button.click()

            # Select "Grams" from the units dropdown
            units_dropdown = Select(self.driver.find_element(By.NAME, 'budwire_product_units'))
            units_dropdown.select_by_visible_text('Grams')

            # Select payment terms (example: "Cash on Delivery")
            payment_terms_dropdown = Select(self.driver.find_element(By.NAME, 'budwire_payment_terms'))
            payment_terms_dropdown.select_by_visible_text('Cash on Delivery')

            # Set regular price
            self.driver.find_element(By.ID, '_regular_price').send_keys('19.99')

            # Set the quantity
            quantity_input = self.driver.find_element(By.NAME, '_stock')
            quantity_input.clear()
            quantity_input.send_keys('9999')  # Example quantity, change as needed

            # Click the category dropdown to open it using JavaScript
            self.driver.execute_script("document.getElementById('product_main_category').click()")

            # Select "Flower" from the category list using JavaScript
            flower_option = self.driver.execute_script(
                "var options = document.getElementById('product_main_category').options;"
                "for (var i = 0; i < options.length; i++) {"
                "   if (options[i].text === 'Flower') {"
                "       options[i].selected = true;"
                "       break;"
                "   }"
                "}"
            )

            # Enter short description into the iframe
            self.driver.switch_to.frame(self.driver.find_element(By.ID, "post_excerpt_ifr"))
            short_description_field = self.driver.find_element(By.TAG_NAME, "body")
            short_description_field.clear()
            short_description_field.send_keys("This is a test short description.")
            self.driver.switch_to.default_content()

            # Fill in the THC information
            thc_min = "1"
            thc_max = "2"
            self.driver.find_element(By.ID, 'budwire_thc_lebel_min_input').send_keys(thc_min)
            self.driver.find_element(By.ID, 'budwire_thc_lebel_max_input').send_keys(thc_max)

            # Fill in the CBD information
            cbd_level_min = self.driver.find_element(By.ID, 'budwire_cbd_level_min_input')
            cbd_level_min.clear()
            cbd_level_min.send_keys('10')  # Example value, change as needed

            # Reference the CBD level max number input within the second <p> tag
            cbd_level_max_number = self.driver.find_element(By.XPATH,
                                                            "(//input[@id='budwire_cbd_level_min_input' and @type='number' and @oninput='this.previousElementSibling.value = this.value'])[2]")
            cbd_level_max_number.clear()
            cbd_level_max_number.send_keys('20')  # Example value, change as needed

            # Click on the "Save Product" button
            save_button = self.driver.find_element(By.ID, 'publish')
            save_button.click()

            time.sleep(2)  # Adding a slight delay to ensure the fields are saved before taking a screenshot
            screenshot = self.take_screenshot('create_new_product')

            # Wait for the success message to appear
            success_message = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'dokan-message')]//strong[contains(text(), 'Success!')]"))
            )

            success = "Success!" in success_message.text

            # Capture the current URL after saving the product
            page_url = self.driver.current_url

            self.results.append({
                'test': 'Create New Product',
                'success': success,
                'load_time': load_time,
                'screenshot': screenshot,
                'url': page_url
            })
            return success
        except Exception as e:
            print(f"An error occurred during product creation: {e}")
            screenshot = self.take_screenshot('create_new_product')
            self.results.append({
                'test': 'Create New Product',
                'success': False,
                'load_time': load_time,
                'screenshot': screenshot,
                'url': self.driver.current_url
            })
            return False

    def generate_report(self):
        report_date = datetime.now().strftime("%Y-%m-%d")
        self.pdf.set_auto_page_break(auto=True, margin=15)

        # Add the first page with a title
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=16, style='B')
        self.pdf.cell(200, 10, txt=f"Website Testing Report - {report_date}", ln=True, align="C")

        # Add some spacing
        self.pdf.ln(10)

        # Summary table header
        self.pdf.set_font("Arial", size=14, style='B')
        self.pdf.set_fill_color(200, 220, 255)
        self.pdf.cell(190, 10, "Summary of Test Results", 1, ln=True, align="C", fill=True)

        # Build the summary table HTML
        summary_table_html = """
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #c8dcff;">
                <th>Test</th>
                <th>Success</th>
                <th>Load Time (s)</th>
                <th>URL</th>
            </tr>
        """

        # Summary table columns
        self.pdf.set_font("Arial", size=12, style='B')
        self.pdf.cell(40, 10, "Test", 1, 0, "C", fill=True)
        self.pdf.cell(30, 10, "Success", 1, 0, "C", fill=True)
        self.pdf.cell(40, 10, "Load Time (s)", 1, 0, "C", fill=True)
        self.pdf.cell(80, 10, "URL", 1, 1, "C", fill=True)

        # Summary table rows
        self.pdf.set_font("Arial", size=12)
        for idx, result in enumerate(self.results, start=1):
            truncated_url = self.truncate_text(result['url'], 40)  # Adjust the max length to 40 characters
            self.pdf.cell(40, 10, result['test'], 1, 0, "C")
            self.pdf.cell(30, 10, 'Yes' if result['success'] else 'No', 1, 0, "C")
            self.pdf.cell(40, 10, f"{result['load_time']:.2f}", 1, 0, "C")
            self.pdf.cell(80, 10, truncated_url, 1, 1, "C")

            # Add rows to the summary table HTML
            summary_table_html += f"""
            <tr>
                <td>{result['test']}</td>
                <td>{'Yes' if result['success'] else 'No'}</td>
                <td>{result['load_time']:.2f}</td>
                <td>{truncated_url}</td>
            </tr>
            """

        summary_table_html += "</table>"

        # Adding detailed results with screenshots
        for result in self.results:
            self.pdf.add_page()

            # Add the test details
            self.pdf.set_font("Arial", size=14, style='B')
            self.pdf.cell(200, 10, txt=f"Test: {result['test']}", ln=True)

            self.pdf.set_font("Arial", size=12)
            self.pdf.cell(200, 10, txt=f"Success: {'Yes' if result['success'] else 'No'}", ln=True)
            self.pdf.cell(200, 10, txt=f"Load Time: {result['load_time']:.2f} seconds", ln=True)
            self.pdf.cell(200, 10, txt=f"URL: {result['url']}", ln=True)

            # Include the screenshot and fit it to the page, centered below the text
            self.add_screenshot_to_pdf(result['screenshot'])

        # Save the PDF
        pdf_filename = f"website_testing_report_{report_date}.pdf"
        self.pdf.output(pdf_filename)

        # Send the email
        self.send_email(pdf_filename, summary_table_html)

    def add_screenshot_to_pdf(self, screenshot_path):
        # Get image dimensions
        with Image.open(screenshot_path) as img:
            img_width, img_height = img.size

        # Calculate dimensions to fit the image on a single page
        max_width = 180
        max_height = 250

        if img_width > max_width or img_height > max_height:
            ratio = min(max_width / img_width, max_height / img_height)
            img_width = int(img_width * ratio)
            img_height = int(img_height * ratio)

        # Center the image on the page
        x_position = (210 - img_width) // 2
        y_position = self.pdf.get_y() + 10

        # Add the image to the PDF
        self.pdf.image(screenshot_path, x=x_position, y=y_position, w=img_width, h=img_height)

        # Add some space after the image
        self.pdf.ln(img_height + 10)

    def send_email(self, pdf_filename, summary_table_html):
        today = datetime.now().strftime("%Y-%m-%d")
        # Gmail SMTP server settings
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        subject = f"Website Testing Report - {today}"
        body = f"""
        <html>
        <body>
            <p>Please find attached the website testing report.</p>
            <p>Screenshots of each test are within the PDF.</p>
            <p>Summary of Test Results:</p>
            {summary_table_html}
        </body>
        </html>
        """

        # Create a multipart message and set headers
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(self.recipient_emails)
        msg["Subject"] = subject

        # Attach body to email
        msg.attach(MIMEText(body, "html"))

        # Attach PDF file
        with open(pdf_filename, "rb") as attachment:
            part = MIMEApplication(attachment.read(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
            msg.attach(part)

        # Create a secure SSL context and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_emails, msg.as_string())

        # Clean up: delete the PDF
        try:
            os.remove(pdf_filename)
        except Exception as e:
            print(f"Error deleting file {pdf_filename}: {e}")

    def close(self):
        self.driver.quit()
        self.clean_up()

    # Usage
if __name__ == "__main__":
    sender_email = "budwirereporting@gmail.com"
    sender_password = "xwni qucr rcud rmnh"
    recipients_email = ["mathew@budwire.ca", "chris@budwire.ca", "broker@budwire.ca"]
    #recipients_email = ["chris@budwire.ca"]
    tester = BudwireTester("https://www.budwire.ca", sender_email, sender_password, recipients_email)

    # Measure load time and test each feature
    tester.register_new_user()
    tester.login_user()
    tester.create_new_product()
    tester.test_marketplace()
    tester.request_sample()
    tester.generate_report()
    tester.close()


