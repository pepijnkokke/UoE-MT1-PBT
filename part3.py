#!/usr/bin/env python
import optparse
import sys
import models
from collections import namedtuple

optparser = optparse.OptionParser()
optparser.add_option("-i", "--input", dest="input", default="data/input", help="File containing sentences to translate (default=data/input)")
optparser.add_option("-t", "--translation-model", dest="tm", default="data/tm", help="File containing translation model (default=data/tm)")
optparser.add_option("-l", "--language-model", dest="lm", default="data/lm", help="File containing ARPA-format language model (default=data/lm)")
optparser.add_option("-n", "--num_sentences", dest="num_sents", default=sys.maxint, type="int", help="Number of sentences to decode (default=no limit)")
optparser.add_option("-k", "--translations-per-phrase", dest="k", default=1, type="int", help="Limit on number of translations to consider per phrase (default=1)")
optparser.add_option("-s", "--stack-size", dest="s", default=1, type="int", help="Maximum stack size (default=1)")
optparser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False,  help="Verbose mode (default=off)")
opts = optparser.parse_args()[0]

tm = models.TM(opts.tm, opts.k)
lm = models.LM(opts.lm)
french = [tuple(line.strip().split()) for line in open(opts.input).readlines()[:opts.num_sents]]

# tm should translate unknown tokens by copying them to the output with
# probability 1. This is a sensible strategy when translating between
# languages in Latin script since unknown tokens are often names or numbers.
for word in set(sum(french,())):
  if (word,) not in tm:
    tm[(word,)] = [models.phrase(word, 0.0)]

########################################################################
# To alter the underlying dynamic program of the decoder, you need only
# modify the state data structure and the three functions below:
# * initial_state()
# * assign_stack(h)
# * extend_state(h,f)
########################################################################

# This data structure is the fundamental object of a dynamic program for
# monotone phrase-based decoding (also known as a semi-Markov model).
# Field k stores the index of the first word which is part of the gap.
# Field j stores the index of the last word which is a part of the gap.
# Field i stores the number of words that have been translated (which are
# always the words from 1 to i). Field lm_state stores the language model
# conditioning context that should be used to compute the probability of
# the next English word in the translation.
state = namedtuple("state", "k, j, i, lm_state")

# generate an initial hypothesis
def initial_state():
  return state(k=0, j=0, i=0, lm_state=lm.begin())

# determine what stack a hypothesis should be placed in
def assign_stack(s):
  return s.i - (s.j - s.k)

# Given a state for which the k, j, and i values have already
# been updated, and a phrase, update the the lm_state.
def update_lm_state(s, phrase, is_end=False):
  # edge weight includes p_TM
  logprob = phrase.logprob

  # add p_LM probabilities for every word in phrase.english
  lm_state = s.lm_state
  for word in phrase.english.split():
    (lm_state, word_logprob) = lm.score(lm_state, word)
    logprob += word_logprob
  # special case: end of sentence
  logprob += lm.end(lm_state) if is_end else 0.0

  # finally, return the new hypothesis
  new_s = state(k=s.k, j=s.j, i=s.i, lm_state=lm_state)
  return (new_s, logprob, phrase)

# Given an input consisting of partial translation state s and
# associated source sentence f, this function should return a list of
# all possible extensions to it. Each extension must be a tuple
# of the form (new_s, logprob, phrase), in which new_s is a new state
# object, and the edge from s to new_s should be labeled by phrase
# with weight logprob.
def extend_state(s, f):

  # Extend the state by introducing a gap.
  if s.k == 0 and s.j == 0:
    new_k = s.i
    for new_j in xrange(new_k,len(f)):
      if f[new_k:new_j] in tm:
        for new_i in xrange(new_j+1,len(f)+1):
          if f[new_j:new_i] in tm:
            for phrase in tm[f[new_j:new_i]]:
              yield update_lm_state(
                state(k=new_k, j=new_j, i=new_i, lm_state=s.lm_state),
                phrase, is_end=new_i == len(f))

  # Extend the state by filling a gap.
  else:
    assert f[s.k:s.j] in tm, \
      "%r is not present in %r" % (f[s.k:s.j], tm)
    for phrase in tm[f[s.k:s.j]]:
      yield update_lm_state(
        state(k=0, j=0, i=s.i, lm_state=s.lm_state), phrase)

  # Extend the state by translating a suffix.
  for new_i in xrange(s.i+1,len(f)+1):
    if f[s.i:new_i] in tm:
      for phrase in tm[f[s.i:new_i]]:
        yield update_lm_state(
          state(k=s.k, j=s.j, i=new_i, lm_state=s.lm_state),
          phrase, is_end=new_i == len(f))

########################################################################
# End of functions requiring modification
########################################################################

# The following code implements a generic stack decoding algorithm
# that is agnostic to the form of a partial translation state.
# It does however assume that all states in stacks[i] represent
# translations of exactly i source words (though they can be any words).
# It shouldn't be necessary to modify this code if you are only
# changing the dynamic program, but you should understand how it works.
sys.stderr.write("Decoding %s...\n" % (opts.input,))
for f in french:
  # a hypothesis is a node in the decoding search graph. It is parameterized
  # by a state object, defined above.
  hypothesis = namedtuple("hypothesis", "logprob, predecessor, phrase, state")

  # create stacks and add initial state
  stacks = [{} for _ in f] + [{}] # add stack for case of no words are covered
  stacks[0][initial_state()] = hypothesis(0.0, None, None, initial_state())
  for stack in stacks[:-1]:
    for h in sorted(stack.itervalues(),key=lambda h: -h.logprob)[:opts.s]: # prune
      for (new_state, logprob, phrase) in extend_state(h.state, f):
        new_h = hypothesis(logprob=h.logprob + logprob,
                           predecessor=h,
                           phrase=phrase,
                           state=new_state)
        j = assign_stack(new_state)
        if new_state not in stacks[j] or stacks[j][new_state].logprob < new_h.logprob: # second case is recombination
          stacks[j][new_state] = new_h
  winner = max(stacks[-1].itervalues(), key=lambda h: h.logprob)
  def extract_english(h):
    return "" if h.predecessor is None else "%s%s " % (extract_english(h.predecessor), h.phrase.english)
  print extract_english(winner)

  # optionally report (Viterbi) log probability of best hypothesis
  if opts.verbose:
    def extract_tm_logprob(h):
      return 0.0 if h.predecessor is None else h.phrase.logprob + extract_tm_logprob(h.predecessor)
    tm_logprob = extract_tm_logprob(winner)
    sys.stderr.write("LM = %f, TM = %f, Total = %f\n" %
      (winner.logprob - tm_logprob, tm_logprob, winner.logprob))
