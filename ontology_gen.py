import bz2
import xml.etree.ElementTree as ET
from rdflib import Graph, Namespace, Literal, OWL, RDFS, RDF, XSD
import re
import mwparserfromhell
import spacy
from dateutil import parser as date_parser
import logging

class LaborOntologyGenerator:
    def __init__(self):
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize namespaces
        self.labor = Namespace("http://example.org/labor/")
        self.event = Namespace("http://example.org/labor/event/")
        self.org = Namespace("http://example.org/labor/organization/")
        self.person = Namespace("http://example.org/labor/person/")
        self.concept = Namespace("http://example.org/labor/concept/")
        self.location = Namespace("http://example.org/labor/location/")
        
        self.g = Graph()
        
        self.g.bind("labor", self.labor)
        self.g.bind("event", self.event)
        self.g.bind("org", self.org)
        self.g.bind("person", self.person)
        self.g.bind("concept", self.concept)
        self.g.bind("location", self.location)
        self.g.bind("owl", OWL)
        self.g.bind("rdfs", RDFS)
        self.g.bind("rdf", RDF)
        
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_trf")
        except:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except:
                self.logger.error("Please install spacy and the English model: python -m spacy download en_core_web_sm")
                raise

    def create_base_ontology(self):
        """Create the foundational structure of the labor ontology."""
        # Main Classes
        classes = {
            # Organizations
            "LaborOrganization": "Base class for all labor organizations",
            "TradeUnion": "A workers' union organization",
            "LaborFederation": "Federation of multiple unions",
            "WorkersCouncil": "Worker representative body",
            "ProfessionalAssociation": "Professional worker organization",
            
            # Events
            "LaborEvent": "Base class for labor-related events",
            "Strike": "Organized work stoppage",
            "Protest": "Labor demonstration or protest",
            "UnionFormation": "Creation of a union",
            "CollectiveBargaining": "Negotiation process",
            "LaborDispute": "Conflict between workers and management",
            
            "LaborPerson": "Base class for people",
            "UnionLeader": "Union leadership position",
            "LaborActivist": "Labor movement activist",
            "UnionMember": "Member of a labor organization",
            "LaborOrganizer": "Person who organizes labor movements",
            
            "LaborConcept": "Base class for labor concepts",
            "WorkersRights": "Rights of workers",
            "CollectiveAction": "Collective worker activities",
            "LaborLaw": "Laws affecting labor",
            "UnionSecurity": "Union security arrangements",
            "BargainingUnit": "Group represented in negotiations",
            
            "LaborLocation": "Base class for locations",
            "Workplace": "Place of employment",
            "UnionHall": "Union meeting place",
            "StrikeSite": "Location of strike activity"
        }
        
        for class_name, description in classes.items():
            class_uri = self.labor[class_name]
            self.g.add((class_uri, RDF.type, OWL.Class))
            self.g.add((class_uri, RDFS.comment, Literal(description)))
        
        properties = {
            "hasAffiliation": ("LaborOrganization", "LaborOrganization", "Indicates organizational affiliation"),
            "representedBy": ("BargainingUnit", "TradeUnion", "Union representation relationship"),
            "hasLeader": ("LaborOrganization", "UnionLeader", "Leadership relationship"),
            "hasMember": ("LaborOrganization", "UnionMember", "Membership relationship"),
            

            "participatesIn": ("LaborOrganization", "LaborEvent", "Participation in events"),
            "organizesEvent": ("LaborOrganization", "LaborEvent", "Event organization"),
            "leadsEvent": ("UnionLeader", "LaborEvent", "Event leadership"),
            "occursAt": ("LaborEvent", "LaborLocation", "Event location"),
            
            "precededBy": ("LaborEvent", "LaborEvent", "Temporal relationship between events"),
            "succeededBy": ("LaborEvent", "LaborEvent", "Temporal relationship between events"),
            
            "advocatesFor": ("LaborOrganization", "WorkersRights", "Advocacy relationship"),
            "governedBy": ("LaborOrganization", "LaborLaw", "Legal governance"),
            "implementsConcept": ("LaborOrganization", "LaborConcept", "Concept implementation"),
            
            "hasHeadquarters": ("LaborOrganization", "LaborLocation", "Organization headquarters"),
            "operatesIn": ("LaborOrganization", "LaborLocation", "Operational area")
        }
        
        for prop_name, (domain, range_class, description) in properties.items():
            prop_uri = self.labor[prop_name]
            self.g.add((prop_uri, RDF.type, OWL.ObjectProperty))
            self.g.add((prop_uri, RDFS.domain, self.labor[domain]))
            self.g.add((prop_uri, RDFS.range, self.labor[range_class]))
            self.g.add((prop_uri, RDFS.comment, Literal(description)))
        
        data_properties = {
            "foundingDate": (XSD.date, "Date of founding"),
            "membershipCount": (XSD.integer, "Number of members"),
            "eventDate": (XSD.date, "Date of event"),
            "description": (XSD.string, "Descriptive text"),
            "website": (XSD.anyURI, "Web presence"),
            "locationAddress": (XSD.string, "Physical address"),
            "startDate": (XSD.date, "Start date of activity"),
            "endDate": (XSD.date, "End date of activity")
        }
        
        for prop_name, (data_type, description) in data_properties.items():
            prop_uri = self.labor[prop_name]
            self.g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            self.g.add((prop_uri, RDFS.range, data_type))
            self.g.add((prop_uri, RDFS.comment, Literal(description)))

    def extract_info_from_wiki_text(self, title, text):
        """Extract structured information from Wikipedia article text."""
        if not text or not title:
            return None
            
        try:
            # Check if the text contains relevant labor-related keywords
            labor_keywords = ['union', 'labor', 'trade', 'worker', 'strike', 'protest', 
                            'collective bargaining', 'industrial action', 'federation']
            
            if not any(keyword in text.lower() for keyword in labor_keywords):
                return None
                
            wiki = mwparserfromhell.parse(text)
            info = {
                'title': title,
                'type': None,
                'founded': None,
                'members': None,
                'location': None,
                'affiliations': [],
                'people': [],
                'events': [],
                'concepts': [],
                'description': None,
                'sections': {}
            }
            
            for template in wiki.filter_templates():
                template_name = str(template.name).strip().lower()
                if 'infobox' in template_name:
                    self.logger.debug(f"Found infobox in {title}")
                    for param in template.params:
                        name = str(param.name).strip().lower()
                        value = str(param.value).strip() if param.value else ''
                        
                        if not value:
                            continue
                            
                        if any(x in name for x in ['type', 'kind']):
                            info['type'] = value
                        elif any(x in name for x in ['found', 'establish', 'start']):
                            info['founded'] = value
                        elif 'member' in name:
                            info['members'] = value
                        elif any(x in name for x in ['location', 'headquarters', 'hq']):
                            info['location'] = value
                        elif any(x in name for x in ['affiliation', 'affiliate']):
                            if value and not value.startswith('{{'):
                                info['affiliations'].append(value)
            
            cleaned_text = text if text else ''
            

            if cleaned_text:
                cleaned_text = re.sub(r'\{\{.*?\}\}', '', cleaned_text)  # Remove templates
                cleaned_text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', cleaned_text)  # Clean wiki links
                cleaned_text = re.sub(r'<ref[^>]*?>.*?</ref>', '', cleaned_text, flags=re.DOTALL)  # Remove references
                cleaned_text = re.sub(r'<ref[^>]*/>', '', cleaned_text)  # Remove self-closing refs
            
            # Split into sections and paragraphs
            sections = re.split(r'(==+.*?==+)', cleaned_text)
            current_section = "Introduction"
            all_paragraphs = []
            section_paragraphs = {}
            
            for section in sections:
                if not section:  # Skip empty sections
                    continue
                    
                section = section.strip()
                if not section:
                    continue
                    
                if re.match(r'==+.*?==+', section):
                    current_section = re.sub(r'=+', '', section).strip()
                    continue
                    
                paragraphs = [p.strip() for p in section.split('\n\n') if p and p.strip()]
                valid_paragraphs = []
                
                for para in paragraphs:
                    if not para:
                        continue
                        
                    try:
                        para = re.sub(r'\s+', ' ', para).strip()
                    except TypeError:
                        continue
                    
                    if (para and len(para) > 30 and 
                        not para.startswith(('File:', 'Image:', '|', '*', '#', '{', '}', 'thumb|')) and
                        not para.startswith('[[') and
                        'thumb|' not in para and
                        not para.startswith('Category:') and
                        not re.match(r'^\s*\|', para)):
                        
                        valid_paragraphs.append(para)
                        all_paragraphs.append(para)
                
                if valid_paragraphs:
                    section_paragraphs[current_section] = valid_paragraphs
            
            if all_paragraphs:
                info['description'] = ' '.join(all_paragraphs)
                info['sections'] = section_paragraphs
            
            if all_paragraphs:
                try:
                    doc = self.nlp(' '.join(all_paragraphs))
                    
                    for ent in doc.ents:
                        if ent.text and isinstance(ent.text, str):
                            if ent.label_ == 'PERSON':
                                if ent.text not in info['people']:
                                    info['people'].append(ent.text)
                            elif ent.label_ == 'ORG':
                                if ent.text not in info['affiliations']:
                                    info['affiliations'].append(ent.text)
                            elif ent.label_ == 'EVENT':
                                if ent.text not in info['events']:
                                    info['events'].append(ent.text)
                except Exception as e:
                    self.logger.error(f"Error in NLP processing for {title}: {str(e)}")
            
            if info['description']:
                concept_patterns = [
                    r'(?:focuses?|focusing) on ([\w\s,]+)',
                    r'(?:specializes?|specializing) in ([\w\s,]+)',
                    r'(?:advocates?|advocating) for ([\w\s,]+)',
                    r'(?:promotes?|promoting) ([\w\s,]+)',
                    r'(?:represents?|representing) ([\w\s,]+)',
                ]
                
                for pattern in concept_patterns:
                    try:
                        matches = re.finditer(pattern, info['description'], re.IGNORECASE)
                        for match in matches:
                            concept = match.group(1).strip()
                            if concept and concept not in info['concepts']:
                                info['concepts'].append(concept)
                    except Exception as e:
                        self.logger.error(f"Error in concept extraction for {title}: {str(e)}")
            
            if (info['description'] or info['founded'] or info['members'] or 
                info['affiliations'] or info['people'] or info['events'] or
                info['concepts']):
                return info
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing article {title}: {str(e)}")
            return None

    def add_instance_to_ontology(self, info):
        """Add extracted information to the ontology."""
        try:
            if not info:
                return
            
            safe_title = re.sub(r'[^a-zA-Z0-9]+', '_', info['title'])
            

            if any(term in info['title'].lower() for term in ['union', 'federation', 'council', 'association']):
                main_uri = self.org[safe_title]
                main_class = self.labor.LaborOrganization
            elif any(term in info['title'].lower() for term in ['strike', 'protest', 'formation', 'dispute']):
                main_uri = self.event[safe_title]
                main_class = self.labor.LaborEvent
            else:
                main_uri = self.concept[safe_title]
                main_class = self.labor.LaborConcept
            
            self.g.add((main_uri, RDF.type, main_class))
            self.g.add((main_uri, RDFS.label, Literal(info['title'])))
            
            if info['description']:
                self.g.add((main_uri, self.labor.description, Literal(info['description'])))
            

            if info['founded']:
                try:
                    date = date_parser.parse(info['founded'])
                    self.g.add((main_uri, self.labor.foundingDate, 
                              Literal(date.date().isoformat(), datatype=XSD.date)))
                except:
                    self.g.add((main_uri, self.labor.foundingDate, Literal(info['founded'])))
            
            if info['members']:
                try:
                    count = int(''.join(filter(str.isdigit, info['members'])))
                    self.g.add((main_uri, self.labor.membershipCount, 
                              Literal(count, datatype=XSD.integer)))
                except:
                    pass
            
            if info['location']:
                loc_uri = self.location[re.sub(r'[^a-zA-Z0-9]+', '_', info['location'])]
                self.g.add((loc_uri, RDF.type, self.labor.LaborLocation))
                self.g.add((main_uri, self.labor.hasHeadquarters, loc_uri))
            
            for affiliation in info['affiliations']:
                aff_uri = self.org[re.sub(r'[^a-zA-Z0-9]+', '_', affiliation)]
                self.g.add((aff_uri, RDF.type, self.labor.LaborOrganization))
                self.g.add((main_uri, self.labor.hasAffiliation, aff_uri))
            
            for person in info['people']:
                person_uri = self.person[re.sub(r'[^a-zA-Z0-9]+', '_', person)]
                self.g.add((person_uri, RDF.type, self.labor.LaborPerson))
                self.g.add((main_uri, self.labor.hasLeader, person_uri))
            
            for event in info['events']:
                event_uri = self.event[re.sub(r'[^a-zA-Z0-9]+', '_', event)]
                self.g.add((event_uri, RDF.type, self.labor.LaborEvent))
                self.g.add((main_uri, self.labor.participatesIn, event_uri))
                
        except Exception as e:
            self.logger.error(f"Error adding {info['title']} to ontology: {str(e)}")

    def process_dump(self, input_path, output_path):
        """Process the labor articles dump and create ontology."""
        self.logger.info("Creating base ontology structure...")
        self.create_base_ontology()
        
        self.logger.info("Processing articles...")
        articles_processed = 0
        articles_added = 0
        
        try:
            with bz2.BZ2File(input_path) as xml_file:
                context = ET.iterparse(xml_file, events=('end',))
                
                for event, elem in context:
                    if elem.tag.endswith('page'):
                        try:
                            ns_match = re.match(r'\{.*\}', elem.tag)
                            ns = ns_match.group(0) if ns_match else ''
                            
                            title_elem = elem.find(f'.//{ns}title')
                            text_elem = elem.find(f'.//{ns}text')
                            
                            if title_elem is not None and text_elem is not None:
                                title = title_elem.text
                                text = text_elem.text if text_elem.text else ""
                                
                                articles_processed += 1
                                
                                if articles_processed % 100 == 0:
                                    self.logger.info(f"Processed {articles_processed} articles, added {articles_added} to ontology")
                                
                                info = self.extract_info_from_wiki_text(title, text)
                                if info:
                                    self.add_instance_to_ontology(info)
                                    articles_added += 1
                                    self.logger.debug(f"Added article: {title}")
                                
                        except Exception as e:
                            self.logger.error(f"Error processing page: {str(e)}")
                            continue
                        
                        finally:
                            elem.clear()
                            
            self.logger.info(f"Saving ontology to {output_path}")
            self.g.serialize(destination=output_path, format='xml')
            self.logger.info(f"Processed {articles_processed} articles total, added {articles_added} to ontology")
            
        except FileNotFoundError:
            self.logger.error(f"Input file not found: {input_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error processing dump: {str(e)}")
            raise

if __name__ == "__main__":
    INPUT_DUMP = "labor-articles-20241020.xml.bz2"
    OUTPUT_OWL = "labor_movement_ontology_transformer_v2.owl"
    
    try:
        generator = LaborOntologyGenerator()
        generator.process_dump(INPUT_DUMP, OUTPUT_OWL)
    except Exception as e:
        logging.error(f"Failed to generate ontology: {str(e)}")
        raise