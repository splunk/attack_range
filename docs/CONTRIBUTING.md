# Contributing to the Project

This document is the single source of truth on how to contribute to this codebase. Please feel free to browse the open issues and file new ones. All feedback is welcome!

----

## Topics

* [Prerequisites](#prerequisites)
    * [Contributor License Agreement](#contributor-license-agreement)
    * [Code of Conduct](#code-of-conduct)
* [Contribution Workflow](#contribution-workflow)
    * [Feature Requests and Bug Reports](#feature-requests-and-bug-reports)
    * [Fixing Issues](#fixing-issues)
    * [Pull Requests](#pull-requests)
    * [Code Review](#code-review)
    * [Documentation](#documentation)
* [Maintainers](#maintainers)

----

## Prerequisites
When contributing to this repository, please first discuss the change you wish to make via a GitHub issue, Slack message, email, or via other channels with the owners of this repository.

##### Contributor License Agreement
At the moment, we can only accept pull requests submitted from either:
* Splunk employees or
* Individuals that have signed our contributors' agreement

If you wish to be a contributing member of our community, please see the agreement [for individuals](https://www.splunk.com/goto/individualcontributions) or [for organizations](https://www.splunk.com/goto/contributions).

##### Code of Conduct
Please make sure to read and observe our [Code of Conduct](contributing/code-of-conduct.md). Please follow it in all of your interactions involving the project.

## Contribution Workflow
Help is always welcome! For example, documentation can always use improvement. There's always code that can be clarified, functionality that can be extended, and tests to be added to guarantee behavior. If you see something you think should be fixed, don't be afraid to own it.

##### Feature Requests and Bug Reports
Have ideas on improvements? See something that needs work? While the community encourages everyone to contribute code, it is also appreciated when someone reports an issue. Please report any issues or bugs you find through [GitHub's issue tracker](https://github.com/splunk/attack_range/issues). 

If you are reporting a bug, please include:

* Your operating system name and version
* Any details about your local setup that might be helpful in troubleshooting (ex. Python interpreter version, Splunk version, etc.)
* Detailed steps to reproduce the bug

We'd also like to hear about your propositions and suggestions. Feel free to submit them as issues and:

* Explain in detail how they should work
* Note that keeping the scope as narrow as possible will make the suggestion easier to implement

##### Fixing Issues
Look through our [issue tracker](https://github.com/splunk/attack_range/issues) to find problems to fix! Feel free to comment and tag corresponding stakeholders or full-time maintainers of this project with any questions or concerns.

##### Pull Requests
What is a "pull request"? It informs the project's core developers about the changes you want to review and merge. Once you submit a pull request, it enters a stage of code review where you and others can discuss its potential modifications and maybe even add more commits to it later on. 

If you want to learn more, please consult this [tutorial on how pull requests work](https://help.github.com/articles/using-pull-requests/) in the [GitHub Help Center](https://help.github.com/).

###### Pre-commit Hooks
We leverage [pre-commit hooks](.pre-commit-config.yaml) in our project to have some basic/local validation of common code artifacts before a commit is recorded. If you would like to learn more about pre-commit hooks please visit the projects [site](https://pre-commit.com/). 

Here's an overview of how you can make a pull request against this project:

1. Fill out the [Splunk Contribution Agreement](https://www.splunk.com/goto/contributions).
2. Fork the [analytic\_story\_execution GitHub repository](https://github.com/splunk/attack_range/issues)
3. Clone your fork using git and create a branch off of master

    ```
    $ git clone git@github.com:YOUR_GITHUB_USERNAME/attack_range.git
    $ cd attack_range

    # This project uses 'master' for all development activity, so create your branch off that
    $ git checkout -b your-bugfix-branch-name master
    ```
    
4. Make your changes, commit, and push (once your tests have passed)

    ```
    $ cd attack_range
    $ git commit -m "<insert helpful commit message>"
    $ git push 
    ```
    
5. Submit a pull request through the GitHub website, using the changes from your forked codebase

##### Code Review
There are two aspects of code review: giving and receiving.

To make it easier for your PR to receive reviews, keep in mind that the reviewers will need you to:
* Follow the project coding conventions
* Write good commit messages
* Break large changes into a logical series of smaller patches which individually make easily understandable changes, and in aggregate solve a broader issue

Reviewers, the people providing the review, are highly encouraged to revisit the [Code of Conduct](contributing/code-of-conduct.md) and must go above and beyond to promote a collaborative, respectful community.

When reviewing PRs from others, [The Gentle Art of Patch Review](http://sage.thesharps.us/2014/09/01/the-gentle-art-of-patch-review/) suggests an iterative series of focuses designed to lead new contributors to positive collaboration, such as:

* Is the idea behind the contribution sound?
* Is the contribution architected correctly?
* Is the contribution polished?

For this project, we require at least one approval. A build from our continuous integration system must also be successful off of your branch. Please note that any new changes made with your existing pull request during review will automatically unapprove and retrigger another build/round of tests.

##### Documentation
We can always use improvements to our documentation! Anyone can contribute to these docs--whether you’re new to the project, you’ve been around a long time, or if you just can’t stand seeing typos. 

Here's what's needed?

1. More complementary documentation. Have you something unclear?
2. More examples or generic templates that others can use.
3. Blog posts, articles, and such are all very appreciated.

You can also edit documentation files directly in the GitHub web interface, without creating a local copy. This can be convenient for small typos or grammar fixes.

## Maintainers

If you need help, feel free to tag one of the active maintainers of this project in a post or comment. We'll do our best to reach out to you as quickly as we can.

```
# Active maintainers marked with (*)

(*) Bhavin Patel
(*) David Dorsey
(*) Jose Hernandez
```

