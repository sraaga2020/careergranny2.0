import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.standoutsearch.com/database-page-url" # Replace with actual search URL
headers = {"User-Agent": "Mozilla/5.0"} # Prevents some basic blocks

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the container for internship listings
opportunities = []
for item in soup.find_all('div', class_='opportunity-card'): # You must inspect the site to find the real class name
    title = item.find('h3').text
    company = item.find('span', class_='company-name').text
    opportunities.append({"title": title, "company": company})

# Save for your AI project
df = pd.DataFrame(opportunities)
df.to_csv("internships_data.csv", index=False)