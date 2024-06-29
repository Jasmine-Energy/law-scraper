import requests
from bs4 import BeautifulSoup

base_url = 'https://leginfo.legislature.ca.gov'


def get_html_content(url):
    """Fetch the HTML content of a given URL."""
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def find_links_in_div(soup, element='div', **kwargs):
    """Find all links within a specified div ID."""
    div = soup.find(element, **kwargs)
    if div:
        return [a.get('href') for a in div.find_all('a', href=True)]
    return []


def get_text_from_manylawssections(soup, url_path):
    """Get text from a div with ID 'manylawsections'."""
    div = soup.find('div', id='manylawsections')
    if div:
        text = div.get_text(strip=True)
        print(f'{url_path}\n{text[:200]}...')
        return text
    return None


def process_expandedbranchcodesid_links(base_url, soup):
    """Process links within the 'expandedbranchcodesid' div and find 'manylawsections'."""
    links = find_links_in_div(soup, 'expandedbranchcodesid')
    for link in links:
        link_soup = BeautifulSoup(get_html_content(base_url + link), 'html.parser')
        text = get_text_from_manylawssections(link_soup, link)
        if text:
            return text
    return None


def main(url):
    """Main function to process the URL and extract text from 'manylawsections'."""
    # base_url = '/'.join(url.split('/')[:-1]) + '/'  # Get base URL to resolve relative links
    initial_soup = BeautifulSoup(get_html_content(url), 'html.parser')
    
    # Step 1: Find all links in 'codesIndexTblLeftdiv'
    links_in_codes_index = find_links_in_div(initial_soup, class_='codesIndexTblLeftdiv')
    
    for link in links_in_codes_index:
        first_level_soup = BeautifulSoup(get_html_content(base_url + link), 'html.parser')
        
        # Step 2: Find all links in 'codestreeForm2'
        links_in_codestree_form = find_links_in_div(first_level_soup, element='form', id='codestreeForm2')
        
        for inner_link in links_in_codestree_form:
            second_level_soup = BeautifulSoup(get_html_content(base_url + inner_link), 'html.parser')
            
            # Step 3: Check for 'manylawsections' div
            text = get_text_from_manylawssections(second_level_soup, inner_link)
            if text:
                return text
            
            # Step 4: If 'manylawsections' not found, check 'expandedbranchcodesid' links
            text = process_expandedbranchcodesid_links(base_url, second_level_soup)
            if text:
                return text
    
    return "No 'manylawsections' div found."

# Example usage
url = 'https://leginfo.legislature.ca.gov/faces/codes.xhtml'
text_content = main(url)
# print(text_content)