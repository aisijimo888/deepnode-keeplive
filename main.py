# First install required system dependencies - fixing the apt-get command with proper line continuation
!apt-get update && apt-get install -y libx11-xcb1 \
    libgtk-3-0 \
    libasound2 \
    xvfb \
    libgbm1 \
    libxss1 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2

# Then install playwright and its dependencies
!pip install playwright
!playwright install
!playwright install-deps

# Now the original code should work
import re
import os
import time
import json
import asyncio
import nest_asyncio  # Add this import
from pathlib import Path
from playwright.async_api import Playwright, async_playwright, expect, TimeoutError

# Rest of the code remains the same...
# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

async def run(playwright: Playwright) -> None:
    # Get credentials from environment variable
    try:
        credentials = os.environ.get('GT_PW', '')
        username, password = credentials.split(' ', 1)
    except ValueError:
        print("Error: GT_PW environment variable not set correctly. Format should be 'username password'")
        username, password = "", ""  # Set empty to continue script execution
    
    # Get URL from environment variable
    url = os.environ.get('DEEP_URL', '')
    if not url:
        print("Warning: DEEP_URL environment variable not set. Will not navigate after login.")
    
    # Launch browser
    browser = await playwright.firefox.launch(headless=True)
    context = await browser.new_context()
    
    # Rest of your original code remains exactly the same...
    # Define cookie file path
    cookie_file = Path("deepnote_cookies.json")
    
    # Load cookies if they exist
    cookie_login_successful = False
    page = None  # Initialize page variable
    
    if cookie_file.exists():
        try:
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print("Loaded cookies from file")
            
            # Test if cookies work by navigating to sign-in page
            page = await context.new_page()
            await page.goto("https://deepnote.com/sign-in")
            print("Navigated to DeepNote sign-in page")
            
            # Wait to see if we get redirected to workspace
            try:
                await page.wait_for_url("**/workspace/**", timeout=10000)
                current_url = page.url
                if re.match(r"https://deepnote.com/workspace/.*", current_url):
                    print("Cookie login successful, redirected to workspace")
                    cookie_login_successful = True
                else:
                    print("Cookie login may have failed, URL doesn't match workspace pattern")
            except TimeoutError:
                print("Cookie login failed, URL didn't change to workspace")
        except Exception as e:
            print(f"Error loading or using cookies: {str(e)}")
            if page:
                await page.close()
            page = await context.new_page()
    else:
        print("No cookie file found, proceeding with password login")
        page = await context.new_page()
    
    try:
        # If cookie login failed or no cookies existed, perform password login
        if not cookie_login_successful:
            if not page or page.is_closed():
                page = await context.new_page()
            
            # Navigate to DeepNote sign-in page
            if page.url != "https://deepnote.com/sign-in":
                await page.goto("https://deepnote.com/sign-in")
                print("Navigated to DeepNote sign-in page")
            
            # Navigate to GitHub login
            await page.get_by_text("Continue with GitHub").click()
            print("Navigated to GitHub login page")
            await asyncio.sleep(5)
            
            # Wait for username field and enter credentials
            try:
                username_field = page.get_by_label("Username or email address")
                await username_field.wait_for(state="visible", timeout=10000)
                await username_field.click()
                await username_field.fill(username)
                print("Entered username")
            except TimeoutError:
                print("Username field not found, but continuing execution")
            
            # Wait for password field and enter credentials
            try:
                password_field = page.get_by_label("Password")
                await password_field.wait_for(state="visible", timeout=10000)
                await password_field.click()
                await password_field.fill(password)
                print("Entered password")
            except TimeoutError:
                print("Password field not found, but continuing execution")
            
            # Click sign in button
            try:
                sign_in_button = page.get_by_role("button", name="Sign in", exact=True)
                await sign_in_button.wait_for(state="visible", timeout=10000)
                await sign_in_button.click()
                print("Clicked sign in button")
                
                # Wait for navigation after login
                await page.wait_for_load_state("networkidle", timeout=30000)
                print("Login completed and page loaded")
                
                # Save cookies after successful login
                cookies = await context.cookies()
                with open(cookie_file, "w") as f:
                    json.dump(cookies, f)
                print("Saved cookies to file")
                
            except TimeoutError:
                print("Sign in button not found or page navigation timeout, but continuing execution")
        
        # Navigate to specified URL if provided
        if url:
            try:
                await page.goto(url)
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
                print(f"Navigated to {url}")
            except TimeoutError:
                print(f"Timeout when navigating to {url}, but continuing execution")
        
        # Click "Run" button if available
        try:
            run_button = page.get_by_text("Run", exact=True)
            await run_button.wait_for(state="visible", timeout=10000)
            await run_button.click()
            print("Clicked 'Run' button")
        except TimeoutError:
            print("'Run' button not found, app maybe stop")
        
        # Look for any text that starts with "Running"
        await asyncio.sleep(10)
        try:
            # Use locator with a more flexible selector - any text that starts with "Running"
            running_text_elements = page.locator("text=/^Running/")
            await running_text_elements.first.wait_for(state="visible", timeout=10000)
            found_text = await running_text_elements.first.text_content()
            print(f"Found running status: '{found_text}'")
            print("app is Running")
        except TimeoutError:
            print("app is not Running - no text starting with 'Running' found")
    
    finally:
        # Always close browser
        if page and not page.is_closed():
            await page.close()
        await context.close()
        await browser.close()
        print("Browser closed")

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

# Now we can safely use asyncio.run()
asyncio.run(main())
