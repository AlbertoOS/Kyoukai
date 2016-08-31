Kyoukai Changelog
=================

Here you can see the list of changes between each Kyoukai release.

Version 1.9.2 (Unreleased)
--------------------------

 - Add ``depth`` property which signifies how deep in the tree the Blueprint is.

 - The routing tree no longer considers matching routes that don't start with the prefix of the blueprint.

 - Add ``tree_path`` property which shows the full tree path to a Blueprint.

Version 1.9.1
-------------

 - Large amount of code clean up relating to the embedded HTTP server.
   The HTTP server now uses httptools to create requests which is more reliable than http_parser.

Version 1.8.6
-------------

 - Add a default static file handler.

Version 1.8.5
-------------

 - Routing tree has been improved by allowing two routes with the same path but different methods to reside in two
   different blueprints.

Version 1.8.4
-------------

 - Error handlers can now error themselves, and this is handled gracefully.

 - If a match is invalid, it will raise a 500 error at compile time, which is usually when routes are first matched.

Version 1.8.3
-------------

 - Converters can now be awaitables.

Version 1.8.2
-------------

 - JSON forms are now lazy loaded when `.form` is called.

Version 1.8.1
-------------

 - Fix crashing at startup without a startup function registered.

 - Fix routing tree not working with multiple URL prefixes.

 - Fix default converters.

Version 1.8.0
-------------

 - Add the ability to override the Request and Response classes used in views with ``app.request_cls`` and
   ``app._response_cls`` respectively.

 - Views now have the ability to change which Route class they use in the decorator.

 - Implement the Werkzeug Debugger on 500 errors if the app is in debug mode.

Version 1.7.3
-------------

 - Add the ability to register a callable to run on startup.
   This callable can be a regular function or a coroutine.

Version 1.7.2
-------------

 - Form handling is now handled by Werkzeug.

 - Add a new attribute, :attr:`kyoukai.request.Request.files` which stores uploaded files from the form passed in.

 - Requests are no longer parsed multiple times.

Version 1.7.0
-------------

 - Overhaul template renderers. This allows easier creation of a template renderer with a specific engine without
   having to use engine-specific code in views.

 - Add a Jinja2 based renderer. This can be enabled by passing ``template_renderer="jinja2"`` in your application
   constructor.

Version 1.6.0
-------------

 - Add converters.
   Converters allow annotations to be added to parameters which will automatically convert the argument passed in to
   that type, if possible.

 - Exception handlers now take an ``exception`` param as the second arg, whcih is the HTTPException that caused this
   error handler to happen.

Version 1.5.0
-------------

 - Large amount of internal codebase re-written.

 - The Blueprint system was overhauled into a tree system which handles routes much better than before.
