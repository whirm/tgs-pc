#!/usr/bin/env python

from distutils.core import setup

# This is a list of files to install, and where
# (relative to the 'root' dir, where setup.py is)
# You could be more specific.
files = ["tgs_pc/*"]

setup(name = "TheGlobalSquare",
    version = "001",
    description = "TheGlobalSquare is a global, decentralized social and organizational environment which respects privacy for individuals and transparency for public organizations and actions.",
    author = "TheGlobalSquare team",
    author_email = "info@theglobalsquare.org",
    url = "http://theglobalsquare.org",
    # Name the folder where your packages live:
    # (If you have other packages (dirs) or modules (py files) then
    # put them into the package directory - they will be found
    # recursively.)
    packages = ['tgs_pc', 'tgs_pc.ui', 'tgs_pc.widgets'],
    # 'package' package must contain files (see list above)
    # I called the package 'package' thus cleverly confusing the whole issue...
    # This dict maps the package name =to=> directories
    # It says, package *needs* these files.
    #package_data = {'tgs_pc' : files },
    # 'runner' is in the root.
    scripts = ["tgs"],
    long_description = """TheGlobalSquare is a global, decentralized social and organizational environment which
respects privacy for individuals and transparency for public organizations and actions. As a social
environment we will facilitate open communication while retaining individual control over privacy.
We support the right of individuals to assemble, associate and collaborate and to choose the manner
of doing so. We support the right of individuals to share information in order to further our education
and progress. We support individual participation in the actions and organizations which affect them.

As a working environment, our goal is to create working structures that allow collaboration on a massive scale.
We strive to eliminate coercive hierarchical structures and centralized authority while also respecting
individual and local autonomy and producing work of the highest quality. We encourage the use of transparency
as communication, Stigmergy and Concentric User Groups as organizational structures, and Epistemic Communities
to provide the highest level of expertise. We encourage working groups that are task and information driven,
not personality driven. We support a worker's right to autonomy, mastery and control over their own work.

TheGlobalSquare will consist of P2P user profiles which will allow communication throughout a variety of
social mediums and will enable global networking between local assemblies, task groups or events. TheGlobalSquare
will work to create secure, global communications infrastructure and hardware and make this widely available.
TheGlobalSquare will allow for the creation of global Systems for mass collaboration on topics of global interest."""
    
    #This next part it for the Cheese Shop
    #classifiers=[
    #    'Development Status :: 4 - Beta',
    #    'Environment :: X11 Applications :: GTK',
    #    'Intended Audience :: End Users/Desktop',
    #    'Intended Audience :: Developers',
    #    'License :: OSI Approved :: GNU General Public License (GPL)',
    #    'Operating System :: POSIX :: Linux',
    #    'Programming Language :: Python',
    #    'Topic :: Desktop Environment',
    #    'Topic :: Text Processing :: Fonts'
    #]
)
