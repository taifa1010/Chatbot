from flask import Flask, render_template, request, redirect, url_for,jsonify
import os
import aiml
from autocorrect import spell
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

nltk.download('wordnet')
lemmatizer = WordNetLemmatizer()

# neo4j implimentation
from py2neo import Graph, Node, Relationship,NodeMatcher
# graph = Graph("bolt://localhost:7687",auth=("dure","123456789"))
graph = Graph( password="1234567890")
app = Flask(__name__)


#***************************PRE TRAINED AIML***********************************

BRAIN_FILE = "./pretrained_model/aiml_pretrained_model.dump"
k = aiml.Kernel()

if os.path.exists(BRAIN_FILE):
    print("Loading from brain file: " + BRAIN_FILE)
    k.loadBrain(BRAIN_FILE)
else:
    print("Parsing aiml files")
    k.bootstrap(learnFiles="./pretrained_model/learningFileList.aiml", commands="load aiml")
    print("Saving brain file: " + BRAIN_FILE)
    k.saveBrain(BRAIN_FILE)

#*****************************TEMPLETE RENDERING**********************************

@app.route("/")
def login():
    return render_template("login.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")


#*****************************LOGIN PROCESS AND VERIFICATION OF USER NODE ************************************
@app.route('/process_login', methods=['POST'])
def process_login():
    user_details = request.json
    username = user_details['username']
    password = user_details['password']
    
    node1 = graph.nodes.match("Person", name=username, password=password).first()

    if node1:
        # User exists, redirect to chatbot template
        return jsonify({'message': 'User exists'})
    else:
        # User does not exist, pass error message to register
        print('User not found or incorrect password! Please register.')
        return jsonify({'message': 'User not found or incorrect password!'})
     

#*********************************SIGNUP PROCESS AND NODE CREATION IN DATABASE *******************************************

@app.route('/process_registration', methods=['POST'])
def process_registration():
    user_details = request.form
    username = user_details.get('username')
    email = user_details.get('email')
    password = user_details.get('password')
    node1 = graph.nodes.match("Person", name=username, email=email).first()
    if node1:
        print("user already exist")
        response = {'message': 'User already exist'}
    else:
        node = Node("Person", name=username,email=email,password=password)
        graph.create(node)
    # Perform registration logic here
        response = {'message': 'Registration successful'}
    return jsonify(response), 200


#*************************** CHAT BOT RESPONSE AND FRIENDSHIP RELATION ***************************************


@app.route("/get")
def get_bot_response():
    query = request.args.get('msg')
    query = [spell(w) for w in query.split()]  # autocorrect misspelled words
    lemmas = [lemmatizer.lemmatize(word) for word in query]  # lemmatize words
    question = " ".join(lemmas)
    response = k.respond(question)

    # Check if the query indicates a friendship relationship
    if 'friend' in lemmas:
        # Extract the names mentioned in the query
        names = [lemma for lemma in lemmas if lemma != 'friend']
        if len(names) == 2:
            user_name = names[0]
            friend_name = names[1]

            # Find or create the user node
            user_node = graph.nodes.match("Person", name=user_name).first()
            if not user_node:
                user_node = Node("Person", name=user_name)
                graph.create(user_node)

            # Find or create the friend node
            friend_node = graph.nodes.match("Person", name=friend_name).first()
            if not friend_node:
                friend_node = Node("Person", name=friend_name)
                graph.create(friend_node)

            # Create a friendship relationship in Neo4j
            relationship = Relationship(user_node, "FRIEND", friend_node)
            graph.create(relationship)

            response = f"{user_name} and {friend_name} are now friends!"

    if response:
        return str(response)
    else:
        return ":)"


if __name__ == "__main__":
    app.run(port='8000')
