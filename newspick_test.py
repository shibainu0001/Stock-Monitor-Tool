# from bs4 import BeautifulSoup
# import requests

# url_search = 'https://www.google.com/search?biw=2513&bih=817&tbm=nws&sxsrf=ALeKk03-PpUbGxYQpIcp6OcJULFASqa_tA%3A1612525818528&ei=-jAdYKb1H9yf1fAPxrac8AU&q=test&oq=test&gs_l=psy-ab.3..0l10.1628056.1628435.0.1628556.4.4.0.0.0.0.112.340.3j1.4.0....0...1c.1.64.psy-ab..0.4.338....0.H4wnL6N3kBo'
# code=requests.get(url_search)
# soup=BeautifulSoup(code.text,"html.parser")
# print(soup.text)

# for link in soup.find_all('a', href=True):
#     print(link['href'])


# from bs4 import BeautifulSoup
# import requests

# headers = {
#     "User-Agent":
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
# }

# response = requests.get(
#     'https://www.google.com/search?hl=en-US&q=best+coockie&tbm=nws&sxsrf=ALeKk009n7GZbzUhUpsMTt89rigSAluBsQ%3A1616683043826&ei=I6BcYP_OMeGlrgTAwLpA&oq=best+coockie&gs_l=psy-ab.3...325216.326993.0.327292.12.12.0.0.0.0.163.1250.2j9.11.0....0...1c.1.64.psy-ab..1.0.0....0.305S8ngx0uo',
#     headers=headers)

# html = response.text
# soup = BeautifulSoup(html, 'lxml')

# print(soup)

# for headings in soup.findAll('div', class_='dbsr'):
#     title = headings.find('div', class_='JheGif nDgy9d').text
#     summary = headings.find('div', class_='Y3v8qd').text
#     link = headings.a['href']
#     print(title)
#     print(summary)
#     print(link)
#     print()



from bs4 import BeautifulSoup
import requests
base_url = "https://news.google.com/search"
params = {
    'q': 'technology',
    'hl': 'en-US',
    'gl': 'US',
    'ceid': 'US:en'
}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...'
}

response = requests.get(base_url, params=params, headers=headers)
html = response.text
print(response.status_code)

soup = BeautifulSoup(html, 'html.parser')
articles = soup.find_all('article')
news_data = []
for art in articles:

    headline_tag = art.find('a', class_='JtKRv')
    title = headline_tag.get_text() if headline_tag else None

    link_tag = art.find('a', class_='WwrzSb') 
    link = link_tag['href'] if link_tag else ''
    if link.startswith('./'):
        link = 'https://news.google.com' + link[1:]

    source_tag = art.find('div', class_="vr1PYe")
    source = source_tag.get_text() if source_tag else None
    time_tag = art.find('time')
    time_text = time_tag.get_text() if time_tag else None

    snippet_tag = art.find('span', class_='fCU_i') # クラス名は実際のHTMLに合わせる必要がある
    if snippet_tag:
        snippet = snippet_tag.get_text()
    else:
        snippet = None
    news_data.append({
        "title": title,
        "source": source,
        "time": time_text,
        "link": link,
        "snippet": snippet
    })

import pprint
pprint.pprint(news_data)

[{'link': 'https://news.google.com/read/CBMivwFBVV95cUxORlI3ZmNiR2RORE44QUp3UDF1R25YNFU1eGFxYkpRVUZUbHZKa0VPTm16RVV0b0pnMU85YTBPRl8td3RfcEVIUlVvQm53c1I4SHFmNVh6T3l3RGtEYmdESEJEbWZFVnBWNUFhb0ZxVlVpR2hQcW1IUlRtZ2JTT1ZWZFM2UER4MVM1VmZ4ejZGeGo2enQwczB2eUZNMTF0WVNxTGh5LXpTLTdGZWwya3d5Ymh4R0pGWU9mUFJ0OGJ1MA?hl=en-US&gl=US&ceid=US%3Aen',
  'snippet': None,
  'source': 'The Economist',
  'time': '21 hours ago',
  'title': 'The Economist is hiring a science and technology correspondent'},
 {'link': 'https://news.google.com/read/CBMi7wFBVV95cUxPWHAwT0ZtcVUyeWgxczFLN3NTNWMxbWFWaE11SHJxZ194ellVUU9oYW9QS3U5M3VTcjVwcVRIQTNHR1JZV2xPZGRzc3RmUkRxR0ZpMnUxVzV2WHU5S19nQkJXYWhESjR2WXhRVUpVNVZWZlNVN05xS2o1MHEzd21PNmNYSFU3OC1zek5xNTI5ekk2dTBBOV9pSF95dEdLUjNGMGNJR0xvaG9xSm1Wa3pRNndGQ3ltVWZ4dVJEc1VPdTVLbjd6NlFfZ1RiSW9YVHNEVHZEc1IxdVNidjlEd2tFZm04NlNJeVFCOVppS1RmOA?hl=en-US&gl=US&ceid=US%3Aen',
  'snippet': None,
  'source': 'Channel 3000',
  'time': '44 minutes ago',
  'title': 'Local school district adapts AI policies as students embrace new '
           'technology'},
 {'link': 'https://news.google.com/read/CBMioAFBVV95cUxPblhtSF9SelZUR3EzQnlTTzV1TzltQTk5M05fSmVoWTBWdWJLTlNjTEFUSGIxSGJDVE45S0NnVWpZRFpteUpwRXBaRTRIV2E4Qk4wbFJUaENiVjMxQ3BoVkZaSmlhOUk3UVl6eS1lb3dyRVFyOGhKTDRYQUk4RU93VUtaZUloMmhwOXJyazl6VC1IVnd3UGdJZWM4MHE4aENv?hl=en-US&gl=US&ceid=US%3Aen',
  'snippet': None,
  'source': 'Federal News Network',
  'time': 'Yesterday',
  'title': 'Through T-REX, DoD seeks to fill technology gaps'},
 {'link': 'https://news.google.com/read/CBMiWkFVX3lxTE1TQ194TXdhc0RDVGZWeDBkb1M0OVlVVnNTMDNNc3RWNThPLTV5NWZrTUYtZXF6M2hsNW5faVlHLUNkOWg1UXhCek0zbG9hY05Ja1ZOX0VabUN6QdIBX0FVX3lxTE9VQ0M1dVZ0dDdJVjBBemNqRV95bkNMYU1hUEpsbEtHdXBsSHlnai1Xcl9uNVFTTE9NdVZuZXJZQ09pSGplZ09wMjVLZm5RNHVDTEtrRFl3UU9ZSjRPbE13?hl=en-US&gl=US&ceid=US%3Aen',
  'snippet': None,
  'source': 'BBC',
  'time': '6 hours ago',
  'title': 'A let off or tougher than it looks? What the Google monopoly '
           'ruling means'}]