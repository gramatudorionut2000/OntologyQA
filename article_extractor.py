import bz2
import re
import gc
from datetime import datetime

def is_labor_related(text, title):

    # Primary labor-related terms
    primary_keywords = {
        'trade union', 'labor union', 'labour union', 'workers union',
        'labor movement', 'labour movement', 'trade unionist',
        'labor federation', 'labour federation', 'union federation',
        'industrial union', 'craft union'
    }
    
    # Secondary keywords
    supporting_keywords = {
        'collective bargaining', 'strike action', 'industrial action',
        'labor rights', 'labour rights', 'workers rights',
        'union organizing', 'labour organizing', 'labor organizing',
        'shop steward', 'union representative', 'union member',
        'picket line', 'labor dispute', 'labour dispute',
        'workers council', 'works council', 'union leadership',
        'organized labor', 'organised labour'
    }
    
    # Terms that might indicate a labor-focused section
    context_keywords = {
        'union membership', 'union activities', 'union campaign',
        'labor agreement', 'collective agreement', 'strike committee',
        'labor relations', 'labour relations', 'workers committee',
        'union dues', 'union election', 'bargaining unit',
        'union contract', 'labor contract', 'union negotiation'
    }
    
    # Exclusion terms
    exclusion_terms = {
        'civil union', 'european union', 'soviet union', 'credit union',
        'union station', 'union pacific', 'union square', 'union jack',
        'union territory', 'student union', 'rugby union', 'union army',
        'union county', 'union city', 'union college', 'union between',
        'union with', 'union of', 'monetary union', 'union league',
        'union parish', 'union bank', 'union club'
    }
    
    text_lower = text.lower()
    title_lower = title.lower()
    
    if any(term in title_lower for term in exclusion_terms):
        return False
    

    text_start = text_lower
    has_primary = (any(keyword in title_lower for keyword in primary_keywords) or
                  any(keyword in text_start for keyword in primary_keywords))
    
    if not has_primary:
        return False
    
    supporting_count = sum(text_lower.count(keyword) for keyword in supporting_keywords)
    
    context_count = sum(text_lower.count(keyword) for keyword in context_keywords)
    

    if any(keyword in title_lower for keyword in primary_keywords):
        return supporting_count >= 1
    else:
        return supporting_count >= 2 and context_count >= 1

def create_wiki_header():
    """Create the header for the new Wikipedia dump file."""
    current_date = datetime.now().strftime("%Y%m%d")
    return f"""<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="0.10" xml:lang="en">
    <siteinfo>
        <sitename>Wikipedia</sitename>
        <dbname>enwiki</dbname>
        <base>https://en.wikipedia.org/wiki/Main_Page</base>
        <generator>Labor Articles Extractor</generator>
        <case>first-letter</case>
        <namespaces>
            <namespace key="0" case="first-letter" />
        </namespaces>
    </siteinfo>"""

def process_wiki_dump(input_path, output_path):
    
    page_count = 0
    labor_related_count = 0
    current_page_content = []
    in_page = False
    
    try:
        with bz2.open(output_path, 'wt', encoding='utf-8') as out_file:
            # Write header
            out_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            out_file.write(create_wiki_header() + '\n')
            
            with bz2.open(input_path, 'rt', encoding='utf-8') as file:
                title = None
                text = None
                
                for line in file:
                    # Check for page start
                    if '<page>' in line:
                        in_page = True
                        current_page_content = [line]
                        title = None
                        text = None
                        continue
                    
                    # If we're inside a page, collect content
                    if in_page:
                        current_page_content.append(line)
                        
                        # Extract title
                        if '<title>' in line and '</title>' in line:
                            title = re.search(r'<title>(.*?)</title>', line)
                            if title:
                                title = title.group(1)
                        
                        # Extract text
                        if '<text' in line:
                            text_start = line
                            text_content = []
                            
                            # If the text tag ends on the same line
                            if '</text>' in line:
                                text = re.search(r'<text.*?>(.*?)</text>', line)
                                if text:
                                    text = text.group(1)
                            else:
                                # Continue collecting text until we find the end tag
                                while '</text>' not in line:
                                    text_content.append(line)
                                    try:
                                        line = next(file)
                                        current_page_content.append(line)
                                    except StopIteration:
                                        break
                                text_content.append(line)
                                text = ''.join(text_content)
                        
                        # Check for page end
                        if '</page>' in line:
                            in_page = False
                            page_count += 1
                            
                            if title and text and is_labor_related(text, title):
                                # Write the complete page content
                                out_file.write(''.join(current_page_content))
                                labor_related_count += 1
                                
                                if labor_related_count % 10 == 0:
                                    print(f"Found labor-related article: {title}")
                            
                            if page_count % 1000 == 0:
                                print(f"Processed {page_count} pages, found {labor_related_count} labor-related articles")
                                gc.collect()
                            
                            current_page_content = []
            
            # Write closing tag
            out_file.write('</mediawiki>')
    
    except Exception as e:
        print(f"Error during parsing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\nFinishing up...")
        print(f"Total pages processed: {page_count}")
        print(f"Labor-related articles found: {labor_related_count}")
        print(f"Output saved to: {output_path}")

if __name__ == "__main__":
    INPUT_DUMP = "enwiki-20241020-pages-articles-multistream.xml.bz2"
    OUTPUT_DUMP = "labor-articles-20241020.xml.bz2"
    
    import os
    if not os.path.exists(INPUT_DUMP):
        print(f"Error: File not found: {INPUT_DUMP}")
    else:
        print(f"File exists and is {os.path.getsize(INPUT_DUMP) / (1024*1024):.2f} MB")
        process_wiki_dump(INPUT_DUMP, OUTPUT_DUMP)