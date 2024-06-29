
import hashlib
import requests
import urllib.parse

from bs4 import BeautifulSoup

"""
https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=BPC&division=1.&title=&part=&chapter=1.&article=
https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=BPC&division=1.&title=&part=&chapter=1.5.&article=
https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=BPC&division=1.&title=&part=&chapter=2.&article=
"""

base_url = 'https://leginfo.legislature.ca.gov'


def request_soup(url):

    response = requests.get(url)
    if response.status_code not in (200, 201):
        raise ValueError('Request failed')

    digest = hashlib.md5(response.content).digest()
    soup = BeautifulSoup(response.content.decode(), 'html.parser')
    return soup, digest


def scrape_page(url, last_digest=None):

    soup, digest = request_soup(url)
    print(f'{digest} == {last_digest}')
    if digest == last_digest:
        print('GOT THE SAME PAGE!')
        return

    div = soup.find('div', id='manylawsections')
    if div is not None:
        print(url)
        print(div.find_next('h3').get_text(strip=True))
        print(div.find_next('h5').get_text(strip=True))
        print(div.get_text(strip=True)[:200]) 
        print(len(div.get_text(strip=True)))
        print('\n')

        query = urllib.parse.urlparse(url).query
        with open(f'data/{query}.txt', 'w') as fp:
            fp.write(div.get_text(strip=True))

        return
    
    form = soup.find('form', id='codestreeForm2')
    if form is not None:
        for tag in form.find_all('div', class_='codes_toc_list'):
            link = tag.find_next('a').get('href')
            scrape_page(f'{base_url}{link}', last_digest=digest)
        return
    
    div = soup.find('div', id ='expandedbranchcodesid')
    if div is not None:
        for tag in div.find_all('a'):
            text = tag.get_text(strip=True)
            if not text.startswith('ARTICLE'): 
                continue
            if text.startswith('ARTICLE 7. Personal') or \
                  text.startswith('ARTICLE 4. Review') or \
                    text.startswith('ARTICLE 5.5. Quality') or \
                    text.startswith('ARTICLE 4.5. Rural') or \
                    text.startswith('ARTICLE 4. Acute') or \
                    text.startswith('ARTICLE 1. Services') or \
                    text.startswith('ARTICLE 7. Certification') or \
                    text.startswith('ARTICLE 6. Hazardous Waste Inspections') or \
                    text.startswith(''):
                print('nOT TODAY!')
                continue
            link = tag.get('href')
            scrape_page(f'{base_url}{link}', last_digest=digest)
        return

    div = soup.find('div', id='codestocheader')
    if div is not None:
        for tag in reversed(div.find_next('div', class_='displaycodeleftmargin').find_all('a')):
            link = tag.get('href')
            if tag.get_text(strip=True) in (
                    'Welfare and Institutions Code - WIC',
                    'Business and Professions Code - BPC',
                    'Civil Code - CIV',
                    'Code of Civil Procedure - CCP',
                    'Commercial Code - COM',
                    'Corporations Code - CORP'
                ):
                print(f'Already finished section: {tag.get_text()}')
                continue
            scrape_page(f'{base_url}{link}', last_digest=digest)
        return

    return


def scrape_law_section(url):

    soup = request_soup(f'{url}')
    div = soup.find(id="manylawsections")
    if div:
        return [div.get_text(strip=True)]
    elif soup.find(id='expandedbranchcodesid'):
        texts = []
        for tag in soup.find(id='expandedbranchcodesid').find_all('a'):
            text, link = tag.get_text(strip=True), tag.get('href')
            if 'ARTICLE' in text:
                # print(text)
                texts.extend(scrape_law_section(f'{base_url}{link}'))
        return texts
    return []


def scrape_law_code(url):

    soup = request_soup(f'{base_url}{url}')
    texts = []
    for tag in soup.find('form', id='codestreeForm2').find_all('a'):
        text, link = tag.get_text(strip=True), tag.get('href')
        if text == 'Expand all' or link == '#':
            continue
        section = scrape_law_section(f'{base_url}{link}')
        texts.append(section)
        print(section)
    return texts


def scrape_california_constitution(url='https://leginfo.legislature.ca.gov/faces/codes.xhtml'):

    soup, digest = request_soup(url)
    for section in ('codesIndexTblRightdiv', 'codesIndexTblMiddiv', 'codesIndexTblLeftdiv'):
        for tag in soup.find('div', class_=section).find_all('a'):
            text, link = tag.get_text(strip=True), tag.get('href')
            print(scrape_law_code(link))


def scrape_toc_page(code='BPC'):

    url = 'https://leginfo.legislature.ca.gov/faces/codedisplayexpand.xhtml?tocCode='
    soup, _ = request_soup(f'{url}{code}')

    div = soup.find('div', id ='expandedbranchcodesid')
    if div is not None:
        for tag in div.find_all('a'):
            text, link = tag.get_text(strip=True), tag.get('href')
            inner_soup, _ = request_soup(f'{base_url}{link}')
            div = inner_soup.find('div', id='manylawsections')
            if div is not None:
                print(url)
                print(div.find_next('h3').get_text(strip=True))
                print(div.find_next('h5').get_text(strip=True))
                print(div.get_text(strip=True)[:200]) 
                print(len(div.get_text(strip=True)))
                print('\n')

                query = urllib.parse.urlparse(f'{base_url}{link}').query
                with open(f'data/{query}.txt', 'w') as fp:
                    fp.write(div.get_text(strip=True))
                continue
            
            div = inner_soup.find('div', id='expandedbranchcodesid')
            if div is not None:
                continue

    # iterate through all 
    return


if __name__ == '__main__':

    codes = (
        # 'RTC',
        # 'PUC',
        # 'PRC',
        # 'FIN',
        # 'CORP',
        # 'EDC',
        # 'ELEC',
        # 'EVID',
        # 'FAM',
        # 'FGC',
        # 'FAC',
        'GOV',
        'HNC',
        'HSC',
        'INS',
        'LAB',
        'MVC',
        'PEN',
        'PROB',
        'PCC',
        'SHC',
        'UIC',
        'VEH',
        'WAT',
    )
    for code in codes:
        scrape_toc_page(code=code)
    # scrape_page('https://leginfo.legislature.ca.gov/faces/codes.xhtml')


