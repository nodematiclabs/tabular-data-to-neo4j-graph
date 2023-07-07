import csv
import random

# List of URLs from the "example.com" domain for a help desk
urls = [
    "http://www.example.com",
    "http://www.example.com/tickets",
    "http://www.example.com/faq",
    "http://www.example.com/knowledge-base",
    "http://www.example.com/live-chat",
    "http://www.example.com/contact",
    "http://www.example.com/downloads",
    "http://www.example.com/community",
    "http://www.example.com/video-tutorials",
    "http://www.example.com/service-status",
    "http://www.example.com/support-policies",
    "http://www.example.com/account",
    "http://www.example.com/billing",
    "http://www.example.com/remote-assistance",
    "http://www.example.com/feedback"
]

# Number of URLs to output in the CSV
num_urls = 200

# Randomly select URLs
source_urls = [random.choice(urls) for _ in range(num_urls)]
target_urls = [random.choice(urls) for _ in range(num_urls)]

# Write the selected URLs to a CSV file
with open('random_nav.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Source URL', 'Target URL'])  # Header row
    for i in range(len(source_urls)):
        writer.writerow([source_urls[i], target_urls[i]])

print(f'{num_urls} random URLs have been written to "random_nav.csv"')
