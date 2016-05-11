# Your First Kyōkai App

In this tutorial, we'll go through how to write your first Kyōkai app.

## Application Skeleton

Strap in with your favourite IDE, and create your first new project. Name it something silly, for example 
`my-first-kyokai-project`. The name doesn't matter, as you probably won't be using it for long.

### Directory layout

Kyōkai projects have a very simple layout.

```
$ ls --tree                                                                                                            

├── app.py
├── static
└── templates
```

There are three components here:

 - `app.py`
 	- This contains the main code for your app. This can be named absolutely anything, but we're naming it `app` for 
 	simplicity's sake.
 	
 - `templates`
 	- This contains all the templates used for rendering things server-side, or for putting your JS stack of doom 
 	inside.
 	
 - `static`
 	- This contains all the static files, such as your five bootstrap theme CSS files, or the millions of JS 
 	libraries you've included.
 	
## Writing the App

Open up `app.py` and add your starting line.

```python
from kyokai import Kyokai
```

This imports the Kyōkai application class from the library, allowing you to create a new object inside your code.

### Routes

Routes in Kyōkai are very simple, and if you have ever used Flask, are similar in style to Flask routes.

Routes are made up of three parts:

 - The path
 	- This is a **regular expression** that matches the path you want your route to handle. This uses standard `re` 
 	syntax. Match groups are automatically extracted and passed to your function, but that is talked about in a later
 	 example.
 	 
 - The allowed methods
 	- This is a list, or set, or other iterable, of allowed HTTP/1.1 methods for the route to handle. If a method (e
 	.g `GET`) is not in the list, the route cannot handle it, and a HTTP 405 error will automatically be passed to 
 	the client.
 	
 - The route itself
 	- Your route is a coroutine that accepts one argument, by default: the client's request object.
 	
 	```python
 	async def some_route(request: kyokai.Request): ...
 	```
 	
We are going to write a very simple route that returns a `Hello, world!` file.

## Creating the route

Routes in Kyōkai are created very similarly to Flask routes: with a decorator.

```python
@app.route("/path", methods=["GET", "POST"])
```

As explained above, the route decorator takes a path and a method.  
This route decorator returns a Route class, but this isn't important right now.

### The Route Coroutine

Your route function __**must**__ be a coroutine. As Kyōkai is async, your code must also be async.

```python
@app.route("/")
async def index(request): ...
```

Inside our route, we are going to return a string containing the rendered text from our template.

### Templates

Templates are stored in `templates/`, obviously. They are partial HTML code, which can have parts in it replaced 
using code inside the template itself, or your view.
 
The default template engine used by Kyōkai is [Mako](http://www.makotemplates.org/), but you can change it around to 
use [Jinja2](http://jinja.pocoo.org/docs/dev/) easily.

For now, we will put normal HTML in our file.

Open up `templates/index.html` and add the following code to it:

`It's current year, and you're still using blocking code? Not <em>me!</em>`  
(note: do not replace current year with the actual current year.)

Save and close the template.

### Rendering the template

Rendering the template inside your Route is very simple; Kyōkai has a utility function to render your template.

```python
@app.route("/")
async def index(request):
	return app.render("index.html")
```

The `app.render` function automatically loads and renders the template file specified, and returns the rendered HTML 
code for you to return.


## Responses

Note, how in the previous coroutine, we simply returned a `str` in our route. This is not similar to `aiohttp` and 
the likes who force you to return a `Response`. You can return a response object in Kyōkai as normal, but for 
convenience sake, you can also return simply a string or a tuple.

These are transparently converted behind the scenes:

```python
r = Response(code=route_result[1] or 200, body=route_result[0], headers=route_result[2] or {})
```

That is, the first item is converted to your response body, the second item (or 200 by default) is used as the 
response code, and the third code is used as the headers.
 
**All return params except the first is optional, if you do not return a Response object.**

## Running your App

Running a Kyōkai app is also simple. It comes with an incredibly fast built-in web server that can be used perfectly 
fine independently, no WSGI server required.
 
Calling it from blocking code is as simple as running:

```python
app.run(host="127.0.0.1", port=4444)
```

The args passed in here are just the default values; they are optional.  
Open up your web browser and point it to http://localhost:4444/. If you have done this correctly, you should see 
something like this:

![example 1](/img/ex1.png)

## Finishing your project

You have completed your first Kyōkai project. For maximum effectiveness, you must now publish it to GitHub.

```bash
$ git init
$ git remote add origin git@github.com:YourName/my-first-kyokai-project.git
$ git commit -a -m "Initial commit, look how cool I am!"
$ git push -u origin master
```


