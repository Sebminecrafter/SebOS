# If not running interactively, don't do anything
[[ $- != *i* ]] && return

# Prevent doublesourcing
if [[ -z "${BASHRCSOURCED}" ]] ; then
  BASHRCSOURCED="Y"
  # the check is bash's default value
  [[ "$PS1" = '\s-\v\$ ' ]] && PS1='[\u@\h \W]\$ '
  case ${TERM} in
    Eterm*|alacritty*|aterm*|foot*|gnome*|konsole*|kterm*|putty*|rxvt*|tmux*|xterm*)
      PROMPT_COMMAND+=('printf "\033]0;Arch Linux - %s@%s:%s\007" "${USER}" "${HOSTNAME%%.*}" "${PWD/#$HOME/\~}"')
      ;;
    screen*)
      PROMPT_COMMAND+=('printf "\033_Arch linux - %s@%s:%s\033\\" "${USER}" "${HOSTNAME%%.*}" "${PWD/#$HOME/\~}"')
      ;;
  esac
fi

if [[ -r /usr/share/bash-completion/bash_completion ]]; then
  . /usr/share/bash-completion/bash_completion
fi

# ANSI color codes
FBLE="\[\033[34m\]" # foreground blue
FCYN="\[\033[36m\]" # foreground cyan
FWHT="\[\033[37m\]" # foreground white

# Prompt
PS1=$FBLE'\u'$FCYN'@'$FBLE'\h'$FCYN':'$FBLE'\w'$FCYN'\$ '$FWHT

alias ls="ls -al --color=auto"
alias update="pacman -Syu"
alias installer="python3 /sebos/install.py"
