import spacy
from rdflib import Literal, Graph, Namespace, RDF, RDFS, OWL
from enum import Enum
import os
from datetime import datetime
import re
import unicodedata

class QuestionType(Enum):
    WHAT = "what"
    WHEN = "when"
    WHERE = "where"
    WHO = "who"
    HOW = "how"
    WHY = "why"
    EVENTS = "events"

class LaborOntologyQA:
    def __init__(self, ontology_path):
        # Load spaCy model
        print("Loading spaCy transformer model...")
        self.nlp = spacy.load("en_core_web_trf")
        
        # Load existing ontology
        print(f"Loading existing ontology from {ontology_path}...")
        self.g = Graph()
        self.g.parse(ontology_path, format="xml")
        
        # Set up namespaces
        self.labor = Namespace("http://example.org/labor/")
        self.qa = Namespace("http://example.org/labor/qa/")
        self.event = Namespace("http://example.org/labor/event/")
        self.org = Namespace("http://example.org/labor/organization/")
        self.person = Namespace("http://example.org/labor/person/")
        self.concept = Namespace("http://example.org/labor/concept/")
        self.location = Namespace("http://example.org/labor/location/")
        
        # Bind namespaces
        self.g.bind("qa", self.qa)
        
        # Create QA-specific structure
        self.create_qa_structure()
        
        print(f"Loaded ontology with {len(self.g)} triples")

    def create_qa_structure(self):
        """Add question-answer related classes and properties to the ontology"""
        self.g.add((self.qa.Question, RDF.type, OWL.Class))
        self.g.add((self.qa.Answer, RDF.type, OWL.Class))
        self.g.add((self.qa.hasQuestion, RDF.type, OWL.ObjectProperty))
        self.g.add((self.qa.hasAnswer, RDF.type, OWL.ObjectProperty))
        self.g.add((self.qa.questionText, RDF.type, OWL.DatatypeProperty))
        self.g.add((self.qa.answerText, RDF.type, OWL.DatatypeProperty))
        self.g.add((self.qa.questionType, RDF.type, OWL.DatatypeProperty))
        
        self.g.add((self.qa.relatedLeader, RDF.type, OWL.ObjectProperty))
        self.g.add((self.qa.relatedEvent, RDF.type, OWL.ObjectProperty))

    def format_person_name(self, person_uri):

        
        # Extract name from URI
        name = str(person_uri).replace('http://example.org/labor/person/', '')
        name = name.replace('_', ' ').strip()
        
        # Handle special characters
        name = unicodedata.normalize('NFKD', name)
        name = ''.join(c for c in name if not unicodedata.combining(c))
        
        # Fix common character replacements
        replacements = {
            'ae': 'ä',
            'oe': 'ö',
            'ue': 'ü',
            'ss': 'ß',
            ' br ': ' ',
            ' br': ''
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        # Capitalize words properly
        name = ' '.join(word.capitalize() for word in name.split())
        
        return name


    def format_event_name(self, event_uri):
        """Format event names from URIs"""
        name = str(event_uri).replace('http://example.org/labor/event/', '')
        name = name.replace('_', ' ').strip()
        return name

    def generate_leader_answer(self, leaders, org_name):
        if not leaders:
            return f"No leadership information is available for {org_name}."
        
        # Convert to list if not already
        if not isinstance(leaders, list):
            leaders = [leaders]
        
        # Format names
        leader_names = [self.format_person_name(leader) for leader in leaders]
        leader_names = [name for name in leader_names if name and len(name) > 1]
        
        if not leader_names:
            return f"No leadership information is available for {org_name}."
        
        if len(leader_names) == 1:
            return f"The leader of {org_name} is {leader_names[0]}."
        else:
            leaders_str = ", ".join(leader_names[:-1]) + f" and {leader_names[-1]}"
            return f"The leaders of {org_name} are {leaders_str}."


    def is_labor_related(self, entity_uri):
        """
        Determine if an entity is directly related to labor movements/organizations
        Returns: bool
        """
        # Keywords that indicate labor relation
        labor_keywords = {
            'union', 'labor', 'labour', 'worker', 'trade', 'strike', 'industrial',
            'federation', 'confederation', 'syndicate', 'guild', 'collective',
            'bargaining', 'activism', 'protest', 'rights', 'socialist', 'communist',
            'anarchist', 'iww', 'afl', 'cio', 'teamster', 'organizer', 'organiser'
        }
        
        # Keywords that indicate non-labor entities
        non_labor_keywords = {
            'church', 'temple', 'mosque', 'synagogue', 'university', 'college',
            'school', 'academy', 'studio', 'gallery', 'museum', 'library',
            'hospital', 'clinic', 'theater', 'cinema', 'restaurant', 'hotel',
            'bank', 'store', 'shop', 'market'
        }
        
        try:
            label = str(self.g.value(entity_uri, RDFS.label)).lower()
            
            description = str(self.g.value(entity_uri, self.labor.description)).lower()
                         
            text_to_check = f"{label} {description}"
            
            for keyword in non_labor_keywords:
                if keyword in text_to_check:
                    return False
                    
                    
            return False
            
        except Exception as e:
            print(f"Error checking labor relation for {entity_uri}: {str(e)}")
            return False


    def generate_events_answer(self, events, org_name):
        """Generate natural language answer for event participation questions"""
        if not events:
            return f"No event participation information is available for {org_name}."
        
        event_names = [self.format_event_name(event) for event in events]
        
        seen = set()
        unique_events = [x for x in event_names if not (x in seen or seen.add(x))]
        
        if len(unique_events) == 1:
            return f"{org_name} has participated in {unique_events[0]}."
        elif len(unique_events) == 2:
            return f"{org_name} has participated in {unique_events[0]} and {unique_events[1]}."
        else:
            events_str = ", ".join(unique_events[:-1]) + f", and {unique_events[-1]}"
            
            if len(unique_events) <= 4:
                return f"{org_name} has participated in {events_str}."
            else:
                summary_events = ", ".join(unique_events[:3]) + ", and other events"
                return f"{org_name} has been involved in multiple labor actions, including {summary_events}."

    def clean_number(self, number_str):
        """Clean and format member numbers"""
        try:
            digits = ''.join(filter(str.isdigit, str(number_str)))
            if len(digits) > 8:
                digits = digits[:7]
            number = int(digits)
            return "{:,}".format(number)
        except:
            return str(number_str)
        
    def clean_value(self, value):
        """Clean individual field values"""
        value = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', value)  # Wiki links
        value = re.sub(r'\[https?://[^\s\]]+\s*([^\]]+)\]', r'\1', value)  # External links
        value = re.sub(r"'''(.*?)'''", r'\1', value)  # Bold
        value = re.sub(r"''(.*?)''", r'\1', value)  # Italic
        value = re.sub(r'<ref>.*?</ref>', '', value)  # References
        value = re.sub(r'<ref.*?/>', '', value)  # Self-closing references
        value = re.sub(r'\{\{.*?\}\}', '', value)  # Templates
        value = value.strip('{}[] \t\n\r')  # Strip extra characters
        return value.strip()

    
    def clean_text(self, text):
        
        text = re.sub(r'<ref[^>]*?>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<ref[^>]*/>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<ref[^>]*?>\s*</ref>', '', text, flags=re.IGNORECASE)
        
        text = re.sub(r'\.\s*\.|\.+', '.', text)
        text = re.sub(r'([.,!?])\s*\1', r'\1', text)
        text = re.sub(r'\s+([.,!?])', r'\1', text)
        text = re.sub(r'([.,!?])([^\s\d"])', r'\1 \2', text)
        
        text = re.sub(r'\s*\[\s*\]\s*', ' ', text)
        text = re.sub(r'\(\s*\)', '', text)

        info = {
            'name': None,
            'full_name': None,
            'members': None,
            'location': None,
            'affiliation': None,
            'founded': None,
            'description': None,
            'national': None,
            'country': None,
            'website': None,
            'key_people': None,
            'publication': None,
            'focus': None,
            'type': None
        }
        
        text = re.sub(r'thumb\|[^\n]*\n?', '', text)
        text = re.sub(r'\[\[File:.*?\]\]', '', text)
        text = re.sub(r'\[\[Image:.*?\]\]', '', text)
        
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        

        paragraphs = text.split('\n')
        cleaned_paragraphs = []
        
        for para in paragraphs:
            para = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', para)
            para = re.sub(r'\[https?://[^\s\]]+\s*([^\]]+)\]', r'\1', para)
            para = re.sub(r"'''(.*?)'''", r'\1', para)
            para = re.sub(r"''(.*?)''", r'\1', para)
            para = re.sub(r'<ref>.*?</ref>', '', para)
            para = re.sub(r'<ref.*?/>', '', para)
            para = re.sub(r'\{\{.*?\}\}', '', para)
            
  
            para = para.strip()
            
            if (len(para) > 50 and 
                not para.startswith(('File:', 'Image:', '|', '*', '#', '{', '}', 'thumb|')) and
                not para.startswith('[[') and
                'thumb|' not in para and
                not para.startswith('Category:') and
                not para.startswith('=') and
                not re.match(r'^\s*\|', para)):
                cleaned_paragraphs.append(para)
        
        if cleaned_paragraphs:
            complete_description = []
            for para in cleaned_paragraphs:
                if len(complete_description) == 0:
                    complete_description.append(para)
                else:
                    current_text = ' '.join(complete_description).lower()
                    if not any(para.lower() in current_text for para_part in para.split('.')):
                        complete_description.append(para)
            
            info['description'] = ' '.join(complete_description)
        
        infobox_patterns = {
            'name': r'\|[\s]*name[\s]*=[\s]*([^|\n}]+)',
            'full_name': r'\|[\s]*full_name[\s]*=[\s]*([^|\n}]+)',
            'members': r'\|[\s]*members[\s]*=[\s]*([0-9,]+(?:\s*\([^)]*\))?)',
            'location': r'\|[\s]*(?:headquarters|location)[\s]*=[\s]*([^|\n}]+)',
            'affiliation': r'\|[\s]*affiliation[\s]*=[\s]*([^|\n}]+)',
            'founded': r'\|[\s]*founded[\s]*=[\s]*([^|\n}]+)',
            'country': r'\|[\s]*(?:country|location_country)[\s]*=[\s]*([^|\n}]+)',
            'website': r'\|[\s]*(?:website|homepage)[\s]*=[\s]*([^|\n}]+)',
            'key_people': r'\|[\s]*key_people[\s]*=[\s]*([^|\n}]+)',
            'publication': r'\|[\s]*publication[\s]*=[\s]*([^|\n}]+)',
            'focus': r'\|[\s]*focus[\s]*=[\s]*([^|\n}]+)',
            'type': r'\|[\s]*type[\s]*=[\s]*([^|\n}]+)'
        }
        
        for key, pattern in infobox_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                value = self.clean_value(value)
                if value and not value.isspace():
                    info[key] = value
        
        return info


    def clean_location(self, location_text):

        location = re.sub(r'(?:http|https)://\S+', '', location_text)
        location = re.sub(r'ref\s*cite\s*web[^r]*?ref', '', location, flags=re.IGNORECASE | re.DOTALL)
        location = re.sub(r'url\s*status[^r]*?archive\s*date.*', '', location, flags=re.IGNORECASE | re.DOTALL)
        
        location = re.sub(r'<ref[^>]*?>.*?</ref>', '', location, flags=re.DOTALL)
        location = re.sub(r'<ref[^>]*/>', '', location)
        
        location = re.sub(r'\s*,\s*', ', ', location)
        location = re.sub(r'\s+', ' ', location)
        
        location = re.sub(r'<ref[^>]*?>.*?</ref>', '', location_text, flags=re.DOTALL)
        location = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', location)
        location = re.sub(r'\{\{.*?\}\}', '', location)
        
        location = re.sub(r'(?:http|https)://\S+', '', location)
        location = re.sub(r'url\s*status.*', '', location, flags=re.IGNORECASE)
        location = re.sub(r'access\s*date.*', '', location, flags=re.IGNORECASE)
        
        location = re.sub(r'(\w+)\s*,\s*(\w{2})\b', r'\1, \2', location)
        
        location = re.sub(r'\s+', ' ', location)
        location = re.sub(r'\s*,\s*', ', ', location)

        location = re.sub(r'\(\s*\)', '', location)
        location = re.sub(r'\[\s*\]', '', location)

        location = re.sub(r'url\s*status.*', '', location, flags=re.IGNORECASE)
        location = re.sub(r'access\s*date.*', '', location, flags=re.IGNORECASE)
        location = re.sub(r'title.*', '', location, flags=re.IGNORECASE)
        
        location = location.strip(' .,')
        
        parts = location.split(',')
        if len(parts) == 2:
            city, state = parts
            return f"{city.strip()}, {state.strip()}"
        
        return location

    def format_location(self, location_str):
        if location_str.startswith('http://example.org/labor/location/'):
            location = location_str.replace('http://example.org/labor/location/', '')
            location = location.replace('_', ' ').strip()
        else:
            location = location_str
            
        return self.clean_location(location)


    def validate_answer_length(self, answer):
        doc = self.nlp(answer)
        token_count = sum(1 for token in doc if not token.is_punct and not token.is_space)
        return token_count >= 5


    def generate_answer(self, question_type, raw_answer, entity_name, predicate=None):
        if question_type == QuestionType.WHAT:
            info = self.clean_text(str(raw_answer))
            
            entity_uri = None
            is_person = False
            for s in self.g.subjects():
                if str(self.g.value(s, RDFS.label)) == entity_name:
                    entity_uri = s
                    if (s, RDF.type, self.labor.Person) in self.g:
                        is_person = True
                    break
            
            # If we don't have enough meaningful information from the infobox or description,
            # try to find additional information from the ontology
            if not info['description'] and not any(info.values()):
                if entity_uri:
                    # Collect information about the entity
                    if is_person:
                        # Handle person-specific information
                        birth_date = self.g.value(entity_uri, self.labor.birthDate)
                        death_date = self.g.value(entity_uri, self.labor.deathDate)
                        roles = list(self.g.objects(entity_uri, self.labor.hasRole))
                        
                        # Build person description
                        parts = []
                        if birth_date or death_date:
                            life_dates = []
                            if birth_date:
                                life_dates.append(f"born {birth_date}")
                            if death_date:
                                life_dates.append(f"died {death_date}")
                            parts.append(f"was a labor leader who {' and '.join(life_dates)}")
                        else:
                            parts.append("was a labor leader")
                            
                        if roles:
                            role_names = [str(role).split('/')[-1].replace('_', ' ') for role in roles]
                            parts.append(f"who served as {', '.join(role_names)}")
                        
                        return f"{entity_name} {' '.join(parts)}."
                    else:
                        org_type = self.g.value(entity_uri, RDF.type)
                        leaders = list(self.g.objects(entity_uri, self.labor.hasLeader))
                        events = list(self.g.objects(entity_uri, self.labor.participatesIn))
                        location = self.g.value(entity_uri, self.labor.hasHeadquarters)
                        members_count = self.g.value(entity_uri, self.labor.membershipCount)
                        
                        parts = [f"{entity_name} is a labor organization"]
                        
                    if leaders:
                        leader_names = [self.format_person_name(leader) for leader in leaders]
                        if len(leader_names) == 1:
                            parts.append(f"led by {leader_names[0]}")
                        else:
                            parts.append(f"led by {', '.join(leader_names[:-1])} and {leader_names[-1]}")
                    
                    if members_count:
                        parts.append(f"representing {self.clean_number(members_count)} members")
                    
                    if location:
                        loc_name = self.format_location(str(location))
                        parts.append(f"based in {loc_name}")
                    
                    if events:
                        event_names = [self.format_event_name(event) for event in events]
                        if len(event_names) == 1:
                            parts.append(f"which has participated in {event_names[0]}")
                        else:
                            parts.append(f"which has participated in events including {', '.join(event_names[:2])}")
                    
                    return " ".join(parts) + "."
        
            if is_person:
                parts = []
                if info['description']:
                    return f"{entity_name} {info['description']}"
                else:
                    parts.append("was a labor leader")
                    if info['focus']:
                        parts.append(f"who focused on {info['focus']}")
                    return f"{entity_name} {' '.join(parts)}."
            else:
                parts = []
                if info['type']:
                    parts.append(f"{entity_name} is a {info['type']}")
                else:
                    pass
                
                if info['description']:
                    parts.append(info['description'])
                else:
                    details = []
                    if info['key_people']:
                        details.append(f"led by {info['key_people']}")
                    if info['members']:
                        details.append(f"representing {self.clean_number(info['members'])} members")
                    if info['location']:
                        details.append(f"based in {info['location']}")
                    elif info['country']:
                        details.append(f"located in {info['country']}")
                    if info['affiliation']:
                        details.append(f"affiliated with {info['affiliation']}")
                    if info['focus']:
                        details.append(f"focusing on {info['focus']}")
                    if info['publication']:
                        details.append(f"publishing {info['publication']}")
                        
                    if details:
                        parts.append(" and ".join(details))
                
                answer = " ".join(parts).strip()
                if not answer.endswith('.'):
                    answer += "."
                
                return answer

               
        elif question_type == QuestionType.HOW:
            members = self.clean_number(raw_answer)
            return f"{entity_name} has {members} members."
                
        elif question_type == QuestionType.WHERE:
            location = self.format_location(raw_answer)
            location = re.sub(r'(\w+)(\s+\1)+', r'\1', location)
            return f"{entity_name} is headquartered in {location}."
                
        elif question_type == QuestionType.WHEN:
            try:
                date_str = str(raw_answer)
                
                start_date_match = re.search(r'\{\{Start date\|(\d{4})\|(\d{1,2})(?:\|(?:\d{1,2}))?\|?.*?\}\}', date_str)
                if start_date_match:
                    year = int(start_date_match.group(1))
                    month = int(start_date_match.group(2))
                    date = datetime(year, month, 1)
                    return f"{entity_name} was founded in {date.strftime('%B %Y')}."
                    
                else:
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                    return f"{entity_name} was founded on {date.strftime('%B %d, %Y')}."
                    
            except:
                raw_answer = re.sub(r'\{\{.*?\}\}', '', str(raw_answer))
                return f"{entity_name} was founded on {raw_answer}."
            
        elif question_type == QuestionType.WHO:
            return self.generate_leader_answer(raw_answer, entity_name)
            
        elif question_type == QuestionType.EVENTS:
            return self.generate_events_answer(raw_answer, entity_name)
        return str(raw_answer)
        

    def add_qa_pair(self, questions, qa_data):
        """Helper method to validate and add a QA pair"""
        if not qa_data or 'answer' not in qa_data:
            return
            
        answer = qa_data['answer']
        if answer and self.validate_answer_length(answer):
            questions.append(qa_data)



    def generate_questions(self):
        """Generate questions based on the existing ontology content"""
        questions = []
        skipped_count = 0
        
        for person in self.g.subjects(RDF.type, self.labor.Person):
            person_name = str(self.g.value(person, RDFS.label))
            if not person_name:
                continue
            
            description = self.g.value(person, self.labor.description)
            if description:
                answer = self.generate_answer(QuestionType.WHAT, description, person_name)
                qa_data = {
                    'id': f"q_person_who_{person_name}",
                    'question': f"Who is {person_name}?",
                    'answer': answer,
                    'type': QuestionType.WHO,
                    'entity_type': 'person'
                }
                self.add_qa_pair(questions, qa_data)
        

        for org in self.g.subjects(RDF.type, self.labor.LaborOrganization):
            org_name = str(self.g.value(org, RDFS.label))
            if not org_name:
                continue
            
            description = self.g.value(org, self.labor.description)
            if description:
                answer = self.generate_answer(QuestionType.WHAT, description, org_name)
                qa_data = {
                    'id': f"q_org_what_{org_name}",
                    'question': f"What is {org_name}?",
                    'answer': answer,
                    'type': QuestionType.WHAT,
                    'entity_type': 'organization'
                }
                self.add_qa_pair(questions, qa_data)
            
            founding_date = self.g.value(org, self.labor.foundingDate)
            if founding_date:
                answer = self.generate_answer(QuestionType.WHEN, founding_date, org_name)
                qa_data = {
                    'id': f"q_org_when_{org_name}",
                    'question': f"When was {org_name} founded?",
                    'answer': answer,
                    'type': QuestionType.WHEN,
                    'entity_type': 'organization'
                }
                self.add_qa_pair(questions, qa_data)
            
            members = self.g.value(org, self.labor.membershipCount)
            if members:
                answer = self.generate_answer(QuestionType.HOW, members, org_name)
                qa_data = {
                    'id': f"q_org_how_{org_name}",
                    'question': f"How many members are in {org_name}?",
                    'answer': answer,
                    'type': QuestionType.HOW,
                    'entity_type': 'organization'
                }
                self.add_qa_pair(questions, qa_data)
            
            location = self.g.value(org, self.labor.hasHeadquarters)
            if location:
                answer = self.generate_answer(QuestionType.WHERE, location, org_name)
                qa_data = {
                    'id': f"q_org_where_{org_name}",
                    'question': f"Where is {org_name} headquartered?",
                    'answer': answer,
                    'type': QuestionType.WHERE,
                    'entity_type': 'organization'
                }
                self.add_qa_pair(questions, qa_data)
            
            leaders = list(self.g.objects(org, self.labor.hasLeader))
            if leaders:
                answer = self.generate_answer(QuestionType.WHO, leaders, org_name)
                qa_data = {
                    'id': f"q_org_who_{org_name}",
                    'question': f"Who are the leaders of {org_name}?",
                    'answer': answer,
                    'type': QuestionType.WHO,
                    'entity_type': 'organization',
                    'related_leaders': leaders
                }
                self.add_qa_pair(questions, qa_data)
            
            events = list(self.g.objects(org, self.labor.participatesIn))
            if events:
                answer = self.generate_answer(QuestionType.EVENTS, events, org_name)
                qa_data = {
                    'id': f"q_org_events_{org_name}",
                    'question': f"What events has {org_name} participated in?",
                    'answer': answer,
                    'type': QuestionType.EVENTS,
                    'entity_type': 'organization',
                    'related_events': events
                }
                self.add_qa_pair(questions, qa_data)
        
        for q in questions:
            q_uri = self.qa[q['id']]
            self.g.add((q_uri, RDF.type, self.qa.Question))
            self.g.add((q_uri, self.qa.questionText, Literal(q['question'])))
            self.g.add((q_uri, self.qa.answerText, Literal(q['answer'])))
            self.g.add((q_uri, self.qa.questionType, Literal(q['type'].value)))
            
            if 'related_leaders' in q:
                for leader in q['related_leaders']:
                    self.g.add((q_uri, self.qa.relatedLeader, leader))
            
            if 'related_events' in q:
                for event in q['related_events']:
                    self.g.add((q_uri, self.qa.relatedEvent, event))
        
        print(f"\nTotal questions after length filtering: {len(questions)}")
        print(f"Total questions skipped due to short answers: {skipped_count}")
        return questions


    # def enhance_answer_with_context(self, answer, entity_name):
    #     entity_uri = None
    #     for s in self.g.subjects():
    #         if str(self.g.value(s, RDFS.label)) == entity_name:
    #             entity_uri = s
    #             break
                
    #     if not entity_uri:
    #         return answer
            
    #     # Get additional context
    #     context = []
        
    #     # Add founding date if available
    #     founding_date = self.g.value(entity_uri, self.labor.foundingDate)
    #     if founding_date:
    #         context.append(f"Founded in {self.format_date(founding_date)}")
            
    #     # Add location if available
    #     location = self.g.value(entity_uri, self.labor.hasHeadquarters)
    #     if location:
    #         context.append(f"based in {self.format_location(str(location))}")
            
    #     # Add size information if available
    #     members = self.g.value(entity_uri, self.labor.membershipCount)
    #     if members:
    #         context.append(f"representing {self.clean_number(members)} members")
            
    #     # Combine context with original answer
    #     if context:
    #         context_str = ", ".join(context)
    #         if answer.endswith('.'):
    #             answer = answer[:-1]  # Remove period
    #         answer = f"{answer}, {context_str}."
            
    #     return answer
    
    def get_entity_types(self, entity_uri):
        """Get all types for an entity"""
        types = set()
        for t in self.g.objects(entity_uri, RDF.type):
            types.add(str(t))
        return types
        
    # def find_related_entities(self, entity_uri, max_depth=2):
    #     """Find related entities up to a certain depth"""
    #     related = set()
    #     visited = set()
        
    #     def explore(uri, depth):
    #         if depth > max_depth or uri in visited:
    #             return
    #         visited.add(uri)
            
    #         # Get all related entities
    #         for p, o in self.g.predicate_objects(uri):
    #             if isinstance(o, URIRef):
    #                 related.add(o)
    #                 explore(o, depth + 1)
                    
    #     explore(entity_uri, 0)
    #     return related
        
    # def generate_follow_up_questions(self, entity_name):
    #     follow_ups = []
    #     entity_uri = None
        
    #     # Find entity URI
    #     for s in self.g.subjects():
    #         if str(self.g.value(s, RDFS.label)) == entity_name:
    #             entity_uri = s
    #             break
                
    #     if not entity_uri:
    #         return follow_ups
            
    #     # Get entity types
    #     types = self.get_entity_types(entity_uri)
        
    #     # Generate type-specific questions
    #     if str(self.labor.LaborOrganization) in types:
    #         follow_ups.extend([
    #             f"When was {entity_name} founded?",
    #             f"How many members does {entity_name} have?",
    #             f"Who are the leaders of {entity_name}?",
    #             f"What major events has {entity_name} participated in?"
    #         ])
            
    #     elif str(self.labor.LaborEvent) in types:
    #         follow_ups.extend([
    #             f"When did {entity_name} take place?",
    #             f"What organizations were involved in {entity_name}?",
    #             f"What was the outcome of {entity_name}?"
    #         ])
            
    #     elif str(self.labor.Person) in types:
    #         follow_ups.extend([
    #             f"What organizations was {entity_name} affiliated with?",
    #             f"What role did {entity_name} play in the labor movement?",
    #             f"What major events was {entity_name} involved in?"
    #         ])
            
    #     return follow_ups



if __name__ == "__main__":
    try:
        input_path = "labor_movement_ontology_transformer_v2.owl"
        if not os.path.exists(input_path):
            print(f"Error: Could not find ontology file at {input_path}")
            exit(1)
            
        print("Initializing QA system...")
        qa_system = LaborOntologyQA(input_path)
        
        print("\nGenerating questions from the existing ontology...")
        questions = qa_system.generate_questions()
        
        org_questions = {}
        for q in questions:
            org_name = q['question'].split('?')[0].split(' ')[-1]
            if org_name not in org_questions:
                org_questions[org_name] = []
            org_questions[org_name].append(q)
        
        print("\nGenerated Questions and Answers by Organization:")
        print("=" * 80)
        
        for org_name, org_qs in list(org_questions.items())[:5]:
            print(f"\nQuestions about {org_name}:")
            print("-" * 50)
            for q in org_qs:
                print(f"\nQ: {q['question']}")
                print(f"A: {q['answer']}")
            print("-" * 50)
        
        print(f"\nTotal questions generated: {len(questions)}")
        print(f"Total organizations covered: {len(org_questions)}")
        
        output_path = "labor_ontology_with_qa_v2.owl"
        print(f"\nSaving updated ontology to {output_path}...")
        qa_system.g.serialize(destination=output_path, format="xml")
        print("Ontology saved successfully!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise