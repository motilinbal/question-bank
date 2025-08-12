#!/usr/bin/env python3
"""
FreeMedTube.net Video Scraper using Playwright
This script logs into FreeMedTube.net and scrapes video names and links.
Run this script line by line to control the execution process.
"""

# Import required libraries
import os
import asyncio
import json
import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://freemedtube.net/"

async def main():
    # Get credentials from environment variables
    # Make sure to set these before running the script:
    # export FREEMEDTUBE_USERNAME="your_username"
    # export FREEMEDTUBE_PASSWORD="your_password"
    username = os.getenv('FREEMEDTUBE_USERNAME')
    password = os.getenv('FREEMEDTUBE_PASSWORD')

    # Check if credentials are set
    if not username or not password:
        print("Error: Please set FREEMEDTUBE_USERNAME and FREEMEDTUBE_PASSWORD environment variables")
        return

    # Initialize Playwright
    playwright = await async_playwright().start()

    # Launch browser in non-headless mode so you can see it
    # Set slow_mo to make actions visible
    browser = await playwright.chromium.launch(
        headless=False,
        slow_mo=500  # Slow down by 500ms between actions
    )

    # Create a new browser context and page
    context = await browser.new_context()
    page = await context.new_page()

    # Set viewport size
    await page.set_viewport_size({"width": 1280, "height": 720})

    # Navigate to the login page
    print("Navigating to login page...")
    await page.goto("https://freemedtube.net/login")

    # Wait for page to load
    await page.wait_for_load_state("networkidle")

    # Pause to let you see the login page
    print("Login page loaded. Press Enter to continue with login...")
    await asyncio.get_event_loop().run_in_executor(None, input, "")

    # Fill in the login form
    print("Filling in login form...")
    await page.fill('input[name="email"]', username)
    await page.fill('input[name="password"]', password)

    # Pause to let you verify the credentials are filled correctly
    print("Credentials filled. Press Enter to submit the form...")
    await asyncio.get_event_loop().run_in_executor(None, input, "")

    # Click the login button
    print("Submitting login form...")
    await page.click('button[type="submit"]')

    # Wait for navigation to complete
    print("Waiting for login to complete...")
    # await page.wait_for_load_state("networkidle")

    # Check if login was successful by looking for dashboard elements
    try:
        # Wait for either dashboard or error message
        await page.wait_for_selector('.user-info, .dashboard-title, .error-message', timeout=10000)
        
        # Check if we're on the dashboard
        if await page.query_selector('.user-info') or await page.query_selector('.dashboard-title'):
            print("Login successful! You are now on the dashboard.")
        else:
            print("Login may have failed. Please check the browser.")
    except:
        print("Timeout waiting for dashboard elements. Please check the browser.")

    # Pause to let you verify the login was successful
    print("Please verify if login was successful. Press Enter to continue...")
    await asyncio.get_event_loop().run_in_executor(None, input, "")

    await page.goto('https://freemedtube.net/undergrade-library.html')
    await page.wait_for_load_state("networkidle")

    # Get all links on the page
    print("Getting all links on the page...")
    all_links = await page.query_selector_all('a')

    # Filter out the links that are not for courses
    course_links = []
    for link in all_links:
        url = await page.evaluate('(element) => element.getAttribute("href")', link)
        if url and url.startswith('course/'):
            course_links.append(url)

    print("Found the following links:")
    for link in course_links:
        print(link)

    # Collect all course data in memory
    all_courses_data = []
    
    for link in course_links:
        await page.goto(BASE_URL + link)
        await page.wait_for_load_state("networkidle")
        
        # Extract course title
        course_title = await page.title()
        print(f"\nProcessing course: {course_title}")
        
        # Get all chapter sections
        chapters = await page.query_selector_all('.course-chapter')
        
        course_data = {
            'course_title': course_title,
            'course_url': BASE_URL + link,
            'chapters': []
        }
        
        for chapter in chapters:
            # Get chapter title from h2 element
            chapter_header = await chapter.query_selector('h2')
            if chapter_header:
                chapter_title = await chapter_header.inner_text()
                print(f"  Chapter: {chapter_title}")
                
                # Get all video links in this chapter
                video_links = await chapter.query_selector_all('.chapter-body a.chapter-item-link')
                
                chapter_data = {
                    'chapter_title': chapter_title,
                    'videos': []
                }
                
                for video_link in video_links:
                    video_title = await video_link.inner_text()
                    video_url = await video_link.get_attribute('href')
                    
                    # Make sure URL is absolute
                    if video_url and not video_url.startswith('http'):
                        video_url = BASE_URL + video_url if video_url.startswith('/') else f"{BASE_URL}{video_url}"
                    
                    if video_title and video_url:
                        chapter_data['videos'].append({
                            'title': video_title.strip(),
                            'url': video_url
                        })
                        print(f"    Video: {video_title.strip()}")
                
                course_data['chapters'].append(chapter_data)
        
        all_courses_data.append(course_data)
        
        # Pause before processing next course
        print("Press Enter to continue to next course...")
        # await asyncio.get_event_loop().run_in_executor(None, input, "")
        await asyncio.sleep(2)
    
    # Save all data to a single JSON file
    print("\nSaving all data to JSON file...")
    
    # Create a comprehensive data structure
    freemedtube_data = {
        'generated_on': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'base_url': BASE_URL,
        'courses': all_courses_data
    }
    
    # Also create a flat lookup table for easy searching
    video_lookup = {}
    for course in all_courses_data:
        for chapter in course['chapters']:
            for video in chapter['videos']:
                # Create a unique key for each video
                video_key = f"{course['course_title']} - {chapter['chapter_title']} - {video['title']}"
                video_lookup[video_key] = {
                    'title': video['title'],
                    'url': video['url'],
                    'course': course['course_title'],
                    'chapter': chapter['chapter_title']
                }
    
    # Add the lookup table to the data
    freemedtube_data['video_lookup'] = video_lookup
    
    # Save to JSON file with proper encoding
    with open('freemedtube_data.json', 'w', encoding='utf-8') as f:
        json.dump(freemedtube_data, f, indent=2, ensure_ascii=False)
    
    # Calculate statistics
    total_courses = len(all_courses_data)
    total_chapters = sum(len(course['chapters']) for course in all_courses_data)
    total_videos = sum(len(chapter['videos']) for course in all_courses_data for chapter in course['chapters'])
    
    print(f"JSON data file created with {total_courses} courses, {total_chapters} chapters, and {total_videos} videos")
    print("Data saved to freemedtube_data.json")
    print("\nThe file contains:")
    print("- Hierarchical course data with chapters and videos")
    print("- A flat lookup table for easy searching")
    print("- All URLs are properly quoted to handle spaces")



# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())