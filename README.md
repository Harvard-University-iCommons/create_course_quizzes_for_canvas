# Create a quiz in Canvas using "New Quizzes" 

Automated quiz and assessment generation:  take a designated subset of lectures, assignments, etc on Canvas and and use AI to produce a midterm exam draft or a weekly quiz.  The quiz should be easily editable by a human and then created in Canvas in an automated way. 

## Conceptual Overview

1. Get materials from Canvas
2. Produce questions
3. Make a human readable and human-editable format.

   [text2qti](https://github.com/gpoore/text2qti) defines a text-based format for quizzes.  Note that we are using the text-based format defined by this projecct, but not the QTI format for the quizzes -- the quizzes are being created through the Canvas API.
4. Create New Quizzes Quiz in Canvas

   This uses the text based format created in the previous step and a python script that parses the text based format and the Canvas API to create the quiz. 

## Running through the workflow

### Python install dependencies and setup script environment

Install dependences
```
pip install -r requirements.txt
```
Create a `.env` file based on `.env.sample`
```
CANVAS_API_TOKEN=<your canvas token here>
CANVAS_URL=https://canvas.<DOMAIN>.edu
CANVAS_COURSE_ID=<course id for quiz>
CONTENT_CANVAS_COURSE_ID=<course id for content>
```
Note there are two Canvas course ids specified in case you want to get content from one course and create quizzes for another (perhaps a test course).

### Get the Course Materials

Get the materials that will be used to generate the quiz.  You may already have the materials available, or you can pull the materials from a Canvas course site.

  - The python script in this project will download pages and files based on the Canvas course modules structure.
```
python get_canvas_module_items.py
```

  - Alternatively, from Canvas you can export the course (Settings --> Export Course Content).  The contents will have an `.imscc` extension, which is just a zip file, so you can rename the export file with a `.zip`, unzip and access content from there.

### Create a Quiz in a text-based format

Use an AI service (e.g. Gemini, Harvard AI Sandbox, ChatGPT, etc) to produce a plain text file format for the quiz.  The prompt that provides the instruction for the format is in  `prompts/prompt-for-quiz-format.txt`.  Upload the files you want to the quiz to be based on and run the prompt.

Copy the text of the quiz produced into a file. 

### Edit the Quiz

Edit the quiz file with your favorite text editor, or use the basic text editor your system provides (e.g. Notepad on Windows and TextEdit for Mac.) 

The quiz format follows that of the [text2qti](https://github.com/gpoore/text2qti) project.  If you look at the one produced, you should get the idea.  Multiple choice options use a), b), etc, and the correct answer is marked by an asterisk like *c)

```
1. When was Harvard founded
a) 1638
*b) 1636
c) 1620
```

Once you've reviewed the quiz and made any changes you want, you can run the python script that will read the quiz and use the Canvas API to create a quiz!

### Create the quiz in Canvas with

Run
```
python create_canvas_quiz.py path/to/quiz.txt
```

The quiz isn't published, so visit the quiz in Canvas to modify any settings (question and answer shuffling, allowing multiple attempts, etc), set a  due date, and publish it!

### Examples

In the `examples` directory, there is sample content from Harvard's website as well as a sample quiz in the text-based format (`examples\example-harvard-quiz.txt`).