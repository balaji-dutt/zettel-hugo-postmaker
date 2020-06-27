# Rewrite Wikilinks in Zettelkasten as Hugo Links

This repository contains two Python scripts:

- [zettel_link_rewriter.py](#zettel_link_rewriterpy) which can take a folder of Markdown files (or any other compatible format) and 
convert any links that are in `[[wikilink]]` format into a link format that can be used with [Hugo](https://gohugo.io/).
- [zettel_hugo_postmaker.py](#zettel_hugo_postmakerpy) which can take a folder of Markdown files (files with a `.md` extension only) and:
  - Using `pandoc`, convert any citation links in pandoc compatible format into nicely formatted Citation links 
  - Convert any links that are in `[[wikilink]]` format into a link format that can be used with [Hugo](https://gohugo.io/).

### Why?
Most Zettelkasten software today will handle linking between different notes by adding a link using the `[[wikilink]]`
syntax. This is great for reading and writing within the Zettelkasten ecosystem but Hugo does not recognize the `[[wikilink]]` syntax. 
These scripts attempt to give you more inter-operability with Hugo by converting `[[wikilinks]]` into standard Hugo `[wikilink]({{ relref "wikilink" }})` syntax. 

Details about each of the scripts in this repo can be found below.

### zettel_link_rewriter.py

#### Features
- Fully cross-platform. Script was developed in a Windows environment and is extensively tested to work in 
Windows.
- Provides a number of parameters to configure the script. Parameters can be specified either on the command-line or 
via a configuration file. Refer to [zettel_link_rewriter.ini](zettel_link_rewriter.ini) to see an example.
- Handles wikilinks within Markdown code blocks correctly, i.e., does not rewrite them. This includes fenced code blocks, 
inline code snippets and code blocks indented with four spaces. Do note the [Caveats](#caveats) though.
- Minimal dependencies. The script requires only one additional package to be installed (which is because Python's 
built-in `argparse` module is _terrible_.)

#### Dependencies
- Python 3.4 or higher (Script has only been tested with Python 3.8)
- List of packages specified in `requirements.txt`

#### Getting Started
You can use this script by cloning the repo and installing Python and the script dependencies in a Python venv.
```shell
git clone https://github.com/balaji-dutt/zettel-hugo-postmaker.git
python -m venv .venv
./venv/scripts/activate
pip install -r requirements.txt
python zettel_link_rewriter.py
```
Running the script as shown above will make the script run with a set of built-in defaults. But you can configure 
the script either by supplying a list of parameters on the command-line:
```shell
python zettel_link_rewriter.py -v debug -p all --target_files ./dest/
```

Or you can configure the script by passing a path to a configuration file:

```shell
python zettel_link_rewriter.py -c myconfig.ini
```

An explanation of the different parameters the script recognizes are provided below.

#### Parameters

|Parameter|Mandatory|Description|
|---------|---------|-----------|
|`-h`|No|Show a help message|
|`-c` / `--config`|No|Specify path to Configuration file. <br>By default, the script will look for a configuration file named zettel_link_rewriter.ini in the same directory|
|`-v`|No|Verbosity option. Configures the logging level for the script. You can specify 3 levels of verbosity - `warning/info/debug`. The default is `warning`|
|`-f` / `--file`|No|Write log messages to a file instead of on the console.|
|`--source_files`|No|Specify path to directory containing source markdown files to be processed. <br> Default is to use a "source" folder in the current directory.|
|`--target_files`|No|Specify path to directory where processed markdown files should be saved. <br> Default is to use a "dest" folder in the current directory. <br> The folder where markdown files should be saved after processing will be created if it does not exist.|
|`-p` / `--process`|No|Flag to tell the script whether it should process all files in the source directory or only recently modified files.<br> The parameter supports two values - `all` or `modified`|
|`-m` / `--minutes`|No|Specify in minutes the time-limit for finding recently modified files. Can be used with `-p modified` option. <br> If this is not specified, the script will use a default value of `60` minutes.|


### zettel_hugo_postmaker.py

#### Features
- Fully cross-platform. Script was developed in a Windows environment and is extensively tested to work in 
Windows.
- Provides a number of parameters to configure the script. Parameters can be specified either on the command-line or 
via a configuration file. Refer to [zettel_hugo_postmaker.ini](zettel_hugo_postmaker.ini) to see an example.
- Handles _most_ wikilinks within Markdown code blocks correctly, i.e., does not rewrite them. This includes fenced code blocks and 
inline code snippets but **does not exclude** code blocks indented with four spaces. More details in the [Caveats](#caveats) section.

#### Dependencies
- Python 3.4 or higher (Script has only been tested with Python 3.8)
- pandoc installed and available in your `$PATH`
- Valid Bibliography file that can be understood by pandoc.
- Valid Citation Language Style file.
- List of packages specified in `requirements.txt`

#### Getting Started
You can use this script by cloning the repo and installing Python and the script dependencies in a Python venv.
```shell
git clone https://github.com/balaji-dutt/zettel-hugo-postmaker.git
python -m venv .venv
./venv/scripts/activate
pip install -r requirements.txt
python zettel_hugo_postmaker.py -h
```

You can configure the script either by supplying a list of parameters on the command-line:

```shell
python zettel_hugo_postmaker.py --cite TRUE --bib mybib.bib --csl chicago-fullnote-bibliography.csl --source_files ./source/ --target_files ./dest/
```

Or you can configure the script by passing a path to a configuration file:

```shell
python zettel_link_rewriter.py -c myconfig.ini
```

An explanation of the different parameters the script recognizes are provided below.

#### Parameters
|Parameter|Mandatory|Description|
|---------|---------|-----------|
|`-h`|No|Show a help message|
|`-c` / `--config`|No|Specify path to Configuration file. <br>By default, the script will look for a configuration file named zettel_link_rewriter.ini in the same directory|
|`-v`|No|Verbosity option. Configures the logging level for the script. You can specify 3 levels of verbosity - `warning/info/debug`. The default is `warning`|
|`-f` / `--file`|No|Write log messages to a file instead of on the console.|
|`--cite`|Yes|Specify whether pandoc should process citation references in source Markdown files. The parameter recognizes two values - `TRUE` / `FALSE`. <br> Set to `TRUE` by default and requires `--bib` and `--csl` parameters to be supplied as well.|
|`--source_files`|No|Specify path to directory containing source markdown files to be processed. <br> Default is to use a "source" folder in the current directory.|
|`--target_files`|Yes|Specify path to directory where processed markdown files should be saved. <br> Default is to use a "dest" folder in the current directory. <br> The folder where markdown files should be saved after processing will be created if it does not exist.|
|`--bib`|Yes|Specify path to Bibiliography file that should be used by pandoc for looking up citations.|
|`--csl`|Yes|Specify path to Citation Language Style file that should be used by pandoc when formatting citations.|
|`--images`|No|Flag to tell the script if it should extract and rewrite any image links in the source markdown files. The parameter recognizes two values - `yes` / `no`. Default is `no`|
|`--images_in`|No|This parameter must be provided if the `--images` flag is set to `yes`. Allows you to specify path(s) to directories where images linked in source markdown files are saved. <br>This parameter can specified multiple times to include different directories. <br> Path specified must be for the parent folder to where images are saved. For example if images are saved in `/my/images/folder/` (and the image link in the source Markdown file is `![](./images/folder/my.jpg)` then this parameter should be specified as `/my/images/`. <br> Use double quotes for paths with spaces when specifying paths on the command line only. The script will handle paths with spaces specified in the config file automatically.|
|`--images_out`|No|This parameter must be provided if the `--images` flag is set to `yes`. Specify path to directory where pandoc will store images after extracting them from the source markdown files. <br>Images will be saved with a filename equal to the file SHA. <br> The path specified here should be relative to the Hugo site URL - for example /img if images are served from an img folder on the Hugo site. <br>The script will set the images path after extraction based on the name of the last folder in the path. <br> For example, if the parameter is set to `/my/hugo/images/`, the path for images in the output markdown files will be set to `/images/`. <br> It is recommended to create a symlink in the same partition as the target directory for markdown files for this purpose.|
|`--filters`|No|Specify pandoc LUA filter names that should be included when running pandoc. <br>This parameter can specified multiple times to include different filters - note that pandoc processes filters in sequence, so the order is important|                                                                                                                                            
|`-p` / `--process`|No|Flag to tell the script whether it should process all files in the source directory or only recently modified files.<br> The parameter supports two values - `all` or `modified`|                                                                                                                                                                                                                                                                                                                                                
|`-m` / `--minutes`|No|Specify in minutes the time-limit for finding recently modified files. Can be used with `-p modified` option. <br> If this is not specified, the script will use a default value of `60` minutes.|


### Caveats
- In order to avoid processing wikilinks inside code blocks, the `zettel_link_rewriter.py` script will ignore lines beginning with 4 spaces. 
However, this means that a wikilink in a list that is on the 3rd level or deeper will not be converted. In other words:
```
- [[Level 1 wikilink]] # Will be converted
  - [[Level 2 wikilink]] # Will be converted
    - [[Level 3 wikilink]] # Will *NOT BE* converted
      - Any wikilinks in this level or deeper will also not be converted. 
```

- The `zettel_hugo_postmaker.py` script does not skip wikilinks inside code blocks indented with 4 spaces. Hence:

```python
    #!/usr/bin/env python

    print('Hello world')
    # Here is a [[wikilink]] # Will *ALSO BE* converted
```