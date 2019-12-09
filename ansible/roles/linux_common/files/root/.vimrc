colorscheme delek
set bg=dark
syntax on

set ruler
set number
set smarttab
set fileformats=unix,dos,mac " support all three, in this order
set formatoptions=tcqor " t=text, c=comments, q=format with "gq", o,r=autoinsert comment leader
set cindent                             " indent on cinwords
set shiftwidth=4                " set shiftwidth to 4 spaces
set tabstop=4                   " set tab to 4 spaces
set showmatch                   " Show matching brackets/braces/parantheses.
set background=dark     " set background to dark
set showcmd                             " Show (partial) command in status line.
set autowrite                   " Automatically save before commands like :next and :make
set textwidth=98                " My terminal is 98 characters wide
set visualbell                          " Silence the bell, use a flash instead
set cinoptions=:.5s,>1s,p0,t0,(0,g2     " :.5s = indent case statements 1/2 shiftwidth
set cinwords=if,else,while,do,for,switch,case,class,try   " Which keywords should indent
set showmatch
set statusline=%F%m%r%h%w\ [FORMAT=%{&ff}]\ [TYPE=%Y]\ [ASCII=\%03.3b]\ [HEX=\%02.2B]\ [POS=%04l,%04v]\ [%p%%]\ [LEN=%L] "Shows detailed status line with formatting
set laststatus=2 "This Makes the status bar visible
set mat=5
set tabstop=2 shiftwidth=2 expandtab
filetype plugin on
filetype indent on
set modeline
set nocompatible

" vimrc file for following the coding standards specified in PEP 7 & 8.
"
" To use this file, source it in your own personal .vimrc file (``source
" <filename>``) or, if you don't have a .vimrc file, you can just symlink to it
" (``ln -s <this file> ~/.vimrc``).  All options are protected by autocmds
" (read below for an explanation of the command) so blind sourcing of this file
" is safe and will not affect your settings for non-Python or non-C files.
"
"
" All setting are protected by 'au' ('autocmd') statements.  Only files ending
" in .py or .pyw will trigger the Python settings while files ending in *.c or
" *.h will trigger the C settings.  This makes the file "safe" in terms of only
" adjusting settings for Python and C files.
"
" Only basic settings needed to enforce the style guidelines are set.
" Some suggested options are listed but commented out at the end of this file.

" Number of spaces that a pre-existing tab is equal to.
" For the amount of space used for a new tab use shiftwidth.
au BufRead,BufNewFile *py,*pyw,*.c,*.h,*.pl,*.pm,*.php set tabstop=8

" What to use for an indent.
" This will affect Ctrl-T and 'autoindent'.
" Python and PHP: 4 spaces
" C and perl : tabs (pre-existing files) or 4 spaces (new files)
au BufRead,BufNewFile *.py,*pyw,*.php set shiftwidth=4
au BufRead,BufNewFile *.py,*.pyw,*.php set expandtab

fu Select_c_style()
    if search('^\t', 'n', 150)
        set shiftwidth=8
        set noexpandtab
    el
        set shiftwidth=4
        set expandtab
    en
endf
au BufRead,BufNewFile *.c,*.h,*.pl,*.pm,*.php call Select_c_style()
au BufRead,BufNewFile Makefile* set noexpandtab

" Use the below highlight group when displaying bad whitespace is desired.
highlight BadWhitespace ctermbg=red guibg=red

" Display tabs at the beginning of a line in Python mode as bad.
au BufRead,BufNewFile *.py,*.pyw match BadWhitespace /^\t\+/
" Make trailing whitespace be flagged as bad.
au BufRead,BufNewFile *.py,*.pyw,*.c,*.h,*.pl,*.pm,*.php match BadWhitespace /\s\+$/

" Wrap text after a certain number of characters
" Python: 79
" C: 79
" Perl: 79
" PHP: 79
au BufRead,BufNewFile *.py,*.pyw,*.c,*.h,*.pl,*.pm,*.php set textwidth=79

" Turn off settings in 'formatoptions' relating to comment formatting.
" - c : do not automatically insert the comment leader when wrapping based on
"    'textwidth'
" - o : do not insert the comment leader when using 'o' or 'O' from command mode
" - r : do not insert the comment leader when hitting <Enter> in insert mode
" Python and Perl: not needed
" C: prevents insertion of '*' at the beginning of every line in a comment
au BufRead,BufNewFile *.c,*.h set formatoptions-=c formatoptions-=o formatoptions-=r

" Use UNIX (\n) line endings.
" Only used for new files so as to not force existing files to change their
" line endings.
" Python: yes
" C: yes
" Perl: yes
au BufNewFile *.py,*.pyw,*.c,*.h,*.pm,*.php set fileformat=unix


" ----------------------------------------------------------------------------
" The following section contains suggested settings.  While in no way required
" to meet coding standards, they are helpful.

" Set the default file encoding to UTF-8: ``set encoding=utf-8``

" Puts a marker at the beginning of the file to differentiate between UTF and
" UCS encoding (WARNING: can trick shells into thinking a text file is actually
" a binary file when executing the text file): ``set bomb``

" For full syntax highlighting:
let python_highlight_all=1
syntax on

" Automatically indent based on file type: ``filetype indent on``
" Keep indentation level from previous line: ``set autoindent``

" Folding based on indentation: ``set foldmethod=indent``

" Show tabs and trailing spaces.
" Ctrl-K >> for »
" Ctrl-K .M for ·
" (use :dig for list of digraphs)
set list listchars=tab:..,trail:·

" my perl includes pod
let perl_include_pod = 1
" syntax color complex things like @{${"foo"}}
let perl_extended_vars = 1

" Fold the code block when <F2> is pressed
set foldmethod=marker
set makeprg=python\ %
set autowrite
set paste
