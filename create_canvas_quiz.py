#!/usr/bin/env python3
"""
Canvas LMS New Quiz Creator with text2qti Format Support
Creates a New Quiz with questions from text2qti format files using the Canvas API.

Requirements:
- requests library: pip install requests
- python-dotenv library: pip install python-dotenv
- Canvas API token with appropriate permissions
- .env file with configuration (see example below)

Example .env file:
CANVAS_URL=https://your-school.instructure.com
CANVAS_API_TOKEN=your_api_token_here
CANVAS_COURSE_ID=12345

Example text2qti format file:
Quiz title: Sample Quiz
Quiz description: This is a sample quiz.

1. What is 2+3?
a) 6
b) 1
*c) 5

2. Which are prime numbers?
[ ] 4
[*] 5
[*] 7
[ ] 8
"""

import requests
import uuid
import os
import re
import argparse
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv


class Text2QtiParser:
    """
    Parser for text2qti format files.
    Supports multiple choice, multiple answer, true/false, numerical, 
    short answer, essay, and file upload questions.
    """
    
    def __init__(self):
        self.quiz_title = "Quiz"
        self.quiz_description = ""
        self.multiple_attempts = ""
        self.questions = []
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a text2qti format file.
        
        Args:
            file_path: Path to the text2qti format file
            
        Returns:
            Dict containing quiz metadata and questions
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> Dict[str, Any]:
        """
        Parse text2qti format content.
        
        Args:
            content: Text content in text2qti format
            
        Returns:
            Dict containing quiz metadata and questions
        """
        lines = content.split('\n')
        self.questions = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('%'):
                i += 1
                continue
            
            # Parse quiz settings
            if line.lower().startswith('quiz title:'):
                self.quiz_title = line.split(':', 1)[1].strip()
                
            if line.lower().startswith('quiz description:'):
                self.quiz_description = line.split(':', 1)[1].strip()

            if line.lower().startswith('multiple attempts:'):
                self.multiple_attempts = line.split(':', 1)[1].strip()

            # Parse questions (start with number followed by period)
            if re.match(r'^\d+\.\s+', line):
                question, next_i = self._parse_question(lines, i)
                if question:
                    self.questions.append(question)
                i = next_i
                continue
            
            i += 1
        
        return {
            'title': self.quiz_title,
            'description': self.quiz_description,
            'multiple_attempts' : self.multiple_attempts,
            'questions': self.questions
        }
    
    def _parse_question(self, lines: List[str], start_idx: int) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Parse a single question starting at the given line index.
        
        Args:
            lines: List of all lines in the file
            start_idx: Index where the question starts
            
        Returns:
            Tuple of (question_dict, next_line_index)
        """
        question_line = lines[start_idx].strip()
        question_match = re.match(r'^\d+\.\s+(.+)', question_line)
        if not question_match:
            return None, start_idx + 1
        
        question_text = question_match.group(1)
        question = {
            'text': question_text,
            'type': 'multiple_choice',  # Default type
            'choices': [],
            'points': 1.0
        }
        print(question_text)
        i = start_idx + 1
        
        # Look for choices and determine question type
        while i < len(lines):
            line = lines[i].strip()
            
            # Stop if we hit another question or empty line followed by question
            if re.match(r'^\d+\.\s+', line):
                break
            
            # Multiple choice options (a), b), *c))
            choice_match = re.match(r'^(\*?)([a-z])\)\s+(.+)', line)
            if choice_match:
                is_correct = choice_match.group(1) == '*'
                choice_text = choice_match.group(3)
                question['choices'].append({
                    'text': choice_text,
                    'correct': is_correct
                })
                question['type'] = 'multiple_choice'
                i += 1
                continue
            
            # Multiple answer options ([ ], [*])
            multi_choice_match = re.match(r'^\[(.?)\]\s+(.+)', line)
            if multi_choice_match:
                is_correct = False
                is_correct = multi_choice_match.group(1) == '*'
                choice_text = multi_choice_match.group(2)
                question['choices'].append({
                    'text': choice_text,
                    'correct': is_correct
                })
                question['type'] = 'multiple_answer'
                i += 1
                continue
            
            # Numerical answer (= value)
            numerical_match = re.match(r'^=\s+(.+)', line)
            if numerical_match:
                answer = numerical_match.group(1).strip()
                question['type'] = 'numerical'
                question['answer'] = answer
                i += 1
                continue
            
            # Short answer (* answer)
            short_answer_match = re.match(r'^\*\s+(.+)', line)
            if short_answer_match:
                if 'answers' not in question:
                    question['answers'] = []
                question['answers'].append(short_answer_match.group(1))
                question['type'] = 'short_answer'
                i += 1
                continue
            
            # Essay question indicator (three or more underscores)
            if re.match(r'^_{3,}', line):
                question['type'] = 'essay'
                i += 1
                continue
            
            # File upload indicator (three or more circumflex)
            if re.match(r'^\^{3,}', line):
                question['type'] = 'file_upload'
                i += 1
                continue
            
            # Skip empty lines within a question
            if not line:
                i += 1
                continue
            
            # If we don't recognize the line, move to next
            i += 1
        
        # Auto-detect true/false questions
        if question['type'] == 'multiple_choice' and len(question['choices']) == 2:
            choice_texts = [choice['text'].lower() for choice in question['choices']]
            if ('true' in choice_texts and 'false' in choice_texts) or \
               ('yes' in choice_texts and 'no' in choice_texts):
                question['type'] = 'true_false'
        
        return question, i


class CanvasQuizCreator:
    def __init__(self, canvas_url: str, api_token: str):
        """
        Initialize the Canvas Quiz Creator.
        
        Args:
            canvas_url: Base URL for your Canvas instance (e.g., 'https://your-school.instructure.com')
            api_token: Canvas API token with quiz creation permissions
        """
        self.canvas_url = canvas_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
    
    def create_quiz(self, course_id: int, quiz_title: str, instructions: str = "", 
                   points_possible: float = None, **quiz_settings) -> Dict[str, Any]:
        """
        Create a new quiz in Canvas.
        
        Args:
            course_id: Canvas course ID
            quiz_title: Title for the quiz
            instructions: Quiz instructions (HTML allowed)
            points_possible: Total points for the quiz (will be calculated from questions if not provided)
            **quiz_settings: Additional quiz settings (due_at, unlock_at, etc.)
        
        Returns:
            Dict containing the created quiz data
        """
        url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes"
        
        quiz_data = {
            "quiz": {
                "title": quiz_title,
                "instructions": instructions,
                "grading_type": "points",
            }
        }
        
        if points_possible is not None:
            quiz_data["quiz"]["points_possible"] = points_possible
        
        # Add any additional quiz settings
        for key, value in quiz_settings.items():
            quiz_data["quiz"][key] = value
        
        response = requests.post(url, headers=self.headers, json=quiz_data)
        response.raise_for_status()
        
        return response.json()
    
    def create_question_from_parsed(self, course_id: int, assignment_id: int, 
                                  question_data: Dict[str, Any], position: int = None) -> Dict[str, Any]:
        """
        Create a question in Canvas from parsed text2qti data.
        
        Args:
            course_id: Canvas course ID
            assignment_id: Assignment ID of the quiz
            question_data: Parsed question data from text2qti
            position: Position of question in quiz
            
        Returns:
            Dict containing the created question data
        """
        question_type = question_data.get('type', 'multiple_choice')
        
        if question_type == 'multiple_choice':
            return self._create_multiple_choice_question(
                course_id, assignment_id, question_data, position
            )
        elif question_type == 'multiple_answer':
            return self._create_multiple_answer_question(
                course_id, assignment_id, question_data, position
            )
        elif question_type == 'true_false':
            return self._create_true_false_question(
                course_id, assignment_id, question_data, position
            )
        elif question_type == 'essay':
            return self._create_essay_question(
                course_id, assignment_id, question_data, position
            )
        else:
            # Default to multiple choice for unsupported types
            print(f"Warning: Question type '{question_type}' not fully supported, creating as multiple choice")
            return self._create_multiple_choice_question(
                course_id, assignment_id, question_data, position
            )
    
    def _create_multiple_choice_question(self, course_id: int, assignment_id: int, 
                                       question_data: Dict[str, Any], position: int = None) -> Dict[str, Any]:
        """Create a multiple choice question."""
        url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items"
        
        # Generate UUIDs for choices
        choice_data = []
        correct_choice_id = None
        
        for i, choice in enumerate(question_data['choices']):
            choice_id = str(uuid.uuid4())
            choice_data.append({
                "id": choice_id,
                "position": i + 1,
                "itemBody": f"<p>{choice['text']}</p>"
            })
            
            if choice.get('correct', False):
                correct_choice_id = choice_id
        
        item_data = {
            "item": {
                "entry_type": "Item",
                "points_possible": question_data.get('points', 1.0),
                "entry": {
                    "interaction_type_slug": "choice",
                    "title": f"Question",
                    "item_body": f"<p>{question_data['text']}</p>",
                    "calculator_type": "none",
                    "interaction_data": {
                        "choices": choice_data
                    },
                    "properties": {
                        "shuffleRules": {
                            "choices": {
                                "toLock": [],
                                "shuffled": False
                            }
                        },
                        "varyPointsByAnswer": False
                    },
                    "scoring_data": {
                        "value": correct_choice_id
                    },
                    "scoring_algorithm": "Equivalence"
                }
            }
        }
        
        if position is not None:
            item_data["item"]["position"] = position
        
        response = requests.post(url, headers=self.headers, json=item_data)
        response.raise_for_status()
        
        return response.json()
    
    def _create_multiple_answer_question(self, course_id: int, assignment_id: int, 
                                       question_data: Dict[str, Any], position: int = None) -> Dict[str, Any]:
        """Create a multiple answer question."""
        url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items"
        
        # Generate UUIDs for choices
        choice_data = []
        correct_choice_ids = []
        
        for i, choice in enumerate(question_data['choices']):
            choice_id = str(uuid.uuid4())
            choice_data.append({
                "id": choice_id,
                "position": i + 1,
                "itemBody": f"<p>{choice['text']}</p>"
            })
            
            if choice.get('correct', False):
                correct_choice_ids.append(choice_id)
        
        item_data = {
            "item": {
                "entry_type": "Item",
                "points_possible": question_data.get('points', 1.0),
                "entry": {
                    "interaction_type_slug": "multi-answer",
                    "title": f"Question",
                    "item_body": f"<p>{question_data['text']}</p>",
                    "calculator_type": "none",
                    "interaction_data": {
                        "choices": choice_data
                    },
                    "properties": {
                        "shuffleRules": {
                            "choices": {
                                "toLock": [],
                                "shuffled": False
                            }
                        }
                    },
                    "scoring_data": {
                        "value": correct_choice_ids
                    },
                    "scoring_algorithm": "AllOrNothing"
                }
            }
        }
        
        if position is not None:
            item_data["item"]["position"] = position
        
        response = requests.post(url, headers=self.headers, json=item_data)
        response.raise_for_status()
        
        return response.json()
    
    def _create_true_false_question(self, course_id: int, assignment_id: int, 
                                  question_data: Dict[str, Any], position: int = None) -> Dict[str, Any]:
        """Create a true/false question."""
        url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items"
        
        # Determine the correct answer
        correct_answer = True
        for choice in question_data['choices']:
            if choice.get('correct', False):
                choice_text = choice['text'].lower()
                if 'false' in choice_text or 'no' in choice_text:
                    correct_answer = False
                break
        
        item_data = {
            "item": {
                "entry_type": "Item",
                "points_possible": question_data.get('points', 1.0),
                "entry": {
                    "interaction_type_slug": "true-false",
                    "title": f"Question",
                    "item_body": f"<p>{question_data['text']}</p>",
                    "calculator_type": "none",
                    "interaction_data": {
                        "true_choice": "True",
                        "false_choice": "False"
                    },
                    "properties": {},
                    "scoring_data": {
                        "value": correct_answer
                    },
                    "scoring_algorithm": "Equivalence"
                }
            }
        }
        
        if position is not None:
            item_data["item"]["position"] = position
        
        response = requests.post(url, headers=self.headers, json=item_data)
        response.raise_for_status()
        
        return response.json()
    
    def _create_essay_question(self, course_id: int, assignment_id: int, 
                             question_data: Dict[str, Any], position: int = None) -> Dict[str, Any]:
        """Create an essay question."""
        url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items"
        
        item_data = {
            "item": {
                "entry_type": "Item",
                "points_possible": question_data.get('points', 1.0),
                "entry": {
                    "interaction_type_slug": "essay",
                    "title": f"Question",
                    "item_body": f"<p>{question_data['text']}</p>",
                    "calculator_type": "none",
                    "interaction_data": {
                        "rce": True,
                        "essay": None,
                        "word_count": True,
                        "file_upload": False,
                        "spell_check": True,
                        "word_limit_enabled": False
                    },
                    "properties": {},
                    "scoring_data": {
                        "value": ""
                    },
                    "scoring_algorithm": "None"
                }
            }
        }
        
        if position is not None:
            item_data["item"]["position"] = position
        
        response = requests.post(url, headers=self.headers, json=item_data)
        response.raise_for_status()
        
        return response.json()

    def create_multiple_choice_question(self, course_id: int, assignment_id: int, 
                                      question_text: str, choices: List[Dict[str, Any]], 
                                      correct_answer_index: int, points: float = 1.0,
                                      position: int = None, title: str = None) -> Dict[str, Any]:
        """
        Create a multiple choice question in a New Quiz.
        
        Args:
            course_id: Canvas course ID
            assignment_id: Assignment ID of the quiz (from quiz creation response)
            question_text: The question text (HTML allowed)
            choices: List of choice dictionaries with 'text' key
            correct_answer_index: Index of the correct answer (0-based)
            points: Points for this question
            position: Position of question in quiz
            title: Optional title for the question
        
        Returns:
            Dict containing the created question data
        """
        url = f"{self.canvas_url}/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items"
        
        # Generate UUIDs for choices
        choice_data = []
        correct_choice_id = None
        
        for i, choice in enumerate(choices):
            choice_id = str(uuid.uuid4())
            choice_data.append({
                "id": choice_id,
                "position": i + 1,
                "itemBody": f"<p>{choice['text']}</p>"
            })
            
            if i == correct_answer_index:
                correct_choice_id = choice_id
        
        item_data = {
            "item": {
                "entry_type": "Item",
                "points_possible": points,
                "entry": {
                    "interaction_type_slug": "choice",
                    "title": title or f"Question",
                    "item_body": f"<p>{question_text}</p>",
                    "calculator_type": "none",
                    "interaction_data": {
                        "choices": choice_data
                    },
                    "properties": {
                        "shuffleRules": {
                            "choices": {
                                "toLock": [],
                                "shuffled": False  # Set to True if you want shuffled answers
                            }
                        },
                        "varyPointsByAnswer": False
                    },
                    "scoring_data": {
                        "value": correct_choice_id
                    },
                    "scoring_algorithm": "Equivalence"
                }
            }
        }
        
        if position is not None:
            item_data["item"]["position"] = position
        
        response = requests.post(url, headers=self.headers, json=item_data)
        response.raise_for_status()
        
        return response.json()


def create_quiz_from_text2qti_file(file_path: str, course_id: int, canvas_url: str, api_token: str) -> Dict[str, Any]:
    """
    Create a Canvas quiz from a text2qti format file.
    
    Args:
        file_path: Path to the text2qti format file
        course_id: Canvas course ID
        canvas_url: Canvas base URL
        api_token: Canvas API token
        
    Returns:
        Dict containing quiz creation results
    """
    # Parse the text2qti file
    parser = Text2QtiParser()
    quiz_data = parser.parse_file(file_path)
    #print(quiz_data)

    # Initialize quiz creator
    quiz_creator = CanvasQuizCreator(canvas_url, api_token)
    
    # Calculate total points
    total_points = sum(q.get('points', 1.0) for q in quiz_data['questions'])
    
    # Create the quiz
    quiz = quiz_creator.create_quiz(
        course_id=course_id,
        quiz_title=quiz_data['title'],
        instructions=quiz_data['description'],
        points_possible=total_points,
        multiple_attempts=quiz_data['multiple_attempts']
    )
    
    print(f"Quiz '{quiz_data['title']}' created successfully! Quiz ID: {quiz['id']}")
    assignment_id = quiz['id']
    
    # Add questions
    created_questions = []
    for i, question_data in enumerate(quiz_data['questions'], 1):
        try:
            question = quiz_creator.create_question_from_parsed(
                course_id=course_id,
                assignment_id=assignment_id,
                question_data=question_data,
                position=i
            )
            created_questions.append(question)
            print(f"Question {i} ({question_data['type']}) created successfully!")
        except Exception as e:
            print(f"Error creating question {i}: {e}")
    
    return {
        'quiz': quiz,
        'questions': created_questions,
        'total_questions': len(created_questions),
        'total_points': total_points
    }

def main():
    """
    Main function - can be used for testing or as an example.
    """
    parser = argparse.ArgumentParser(description='Create Canvas Classic Quizzes from text2qti format')
    parser.add_argument('filename', help='Path to text2qti format file')
    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()
    
    # Configuration - READ FROM .env FILE
    CANVAS_URL = os.getenv("CANVAS_URL")
    API_TOKEN = os.getenv("CANVAS_API_TOKEN")
    COURSE_ID = os.getenv("CANVAS_COURSE_ID")
    
    # Validate that all required environment variables are set
    if not CANVAS_URL:
        raise ValueError("CANVAS_URL not found in environment variables. Please check your .env file.")
    if not API_TOKEN:
        raise ValueError("CANVAS_API_TOKEN not found in environment variables. Please check your .env file.")
    if not COURSE_ID:
        raise ValueError("CANVAS_COURSE_ID not found in environment variables. Please check your .env file.")
    
    try:
        COURSE_ID = int(COURSE_ID)
    except ValueError:
        raise ValueError("CANVAS_COURSE_ID must be a valid integer in your .env file.")
    
    print(f"Using Canvas URL: {CANVAS_URL}")
    print(f"Using Course ID: {COURSE_ID}")
    quiz_file = args.filename
    
    if quiz_file and os.path.exists(quiz_file):
        print(f"\nCreating quiz from file: {quiz_file}")
        try:
            result = create_quiz_from_text2qti_file(quiz_file, COURSE_ID, CANVAS_URL, API_TOKEN)
            
            print("\n" + "="*50)
            print("QUIZ CREATION COMPLETE!")
            print("="*50)
            print(f"Quiz Title: {result['quiz']['title']}")
            print(f"Quiz ID: {result['quiz']['id']}")
            print(f"Total Points: {result['total_points']}")
            print(f"Questions Created: {result['total_questions']}")
            print(f"Canvas URL: {CANVAS_URL}/courses/{COURSE_ID}/assignments/{result['quiz']['id']}")

        except Exception as e:
            print(f"Error creating quiz from file: {e}")
            return
    
    else:
        # Example usage 2: Manual quiz creation (original functionality)
        print("\nNo file provided.")
        
        # Initialize the quiz creator
        quiz_creator = CanvasQuizCreator(CANVAS_URL, API_TOKEN)

if __name__ == "__main__":    
    main()