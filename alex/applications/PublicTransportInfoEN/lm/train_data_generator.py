#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

if __name__ == '__main__':
    import autopath

import codecs

from datetime import datetime

import random
import argparse

from alex.components.nlg.tools.en import word_for_number
from alex.corpustools.grammar_weighted import GrammarGen, O, A, UA, S

n_samples = 1*1000*1000
default_method = 'norm'#'uniq'#'test'#


def save_data(fn, data):
    """Save sentences to a file.
    :param fn: file name
    :param data: sentences to be saved
    """
    with codecs.open(fn, 'w', 'utf8') as f:
        for s in data:
            f.write(s)
            f.write('\n')


def spell_number_range(start=0, end=10):
    spelled = []
    while end < start:
        spelled.append(word_for_number(start))
        start += 1
    return spelled


def grammar():

    day = A('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    on_day = S('on', day)

    stop = UA().load('./terms/stops.txt')
    street = UA().load('./terms/streets.txt')
    borough = UA().load('./terms/boroughs.txt')
    city = UA().load('./terms/cities.txt')
    state = UA().load('./terms/states.txt')


    # time relative
    one_minute = UA('one minute', 'a minute')
    minute_multiple = UA(*spell_number_range(2, 60))
    minute = A((minute_multiple, 59), (one_minute, 1))
    in_minute = S('in', minute)

    one_hour = UA('one hour', 'an hour', UA('half an hour', 'quarter of an hour', 'hour and a half', 'hour and a quarter'))
    hour_multiple_12 = UA(*spell_number_range(2, 12))
    hour_multiple_24 = UA(*spell_number_range(2, 24))
    multi_hour_12 = S(hour_multiple_12, O(A('and a half', ('and a quarter', 0.3))), 'hours')
    multi_hour_24 = S(hour_multiple_24, O(A('and a half', ('and a quarter', 0.3))), 'hours')
    in_hour_12 = A((multi_hour_12, 11), (one_hour, 1))
    in_hour_24 = A((multi_hour_24, 23), (one_hour, 1))
    in_hour_1224 = A(in_hour_12, (in_hour_24, 0.2))
    in_hour = S('in', in_hour_1224)

    in_explicit = UA('now', 'at once', 'immediately', 'offhand', 'at this time', 'this instant')

    rel_time = A(in_minute, in_hour, (in_explicit, 0.1))


    # time absolute
    am_pm = UA('AM', 'PM', "o'clock", 'in the evening', 'in the morning')
    at_explicit = UA('at midnight', 'at noon', 'in the morning', 'in the evening')
    hour_fraction = UA('half past', 'quarter past', 'quarter to')

    at_hour = S('at', O(hour_fraction), UA(*spell_number_range(1, 12)), am_pm)

    abs_time = A(at_hour, (at_explicit, 0.1))


    # from - to
    location = UA(stop, street, borough, city, state)
    from_location = S('from', location)
    from_location_O = S(O('from', 0.8), location)
    to_location = S('to', location)
    from_to = A(from_location, to_location, S(from_location, to_location))
    from_0_to= A(from_location, to_location, S(from_location_O, to_location))


    # prefixes
    like = S(UA('i would', "i'd"), 'like')
    look = S(O('i'), A(('search', 0.3), 'look'), 'for')
    looking = S(UA("i'm", 'i am'), A(('looking', 0.8), 'searching'), 'for')
    look_for = A((look, 0.2), looking)

    want = UA(like, 'i need', 'i want')
    x_me = UA(S(O('help me'), 'find'), S(UA('find', 'give'), 'me'))

    can_you = S(O('can you', 0.2), UA(x_me, 'get'))
    want_to = S(want, 'to', UA('find', 'get'))

    # connection
    find = UA(can_you, want_to, look_for)
    a_conneciton = S(O('hello', 0.1), find, 'a connection', from_to)

    # go by (vehicle)
    i_dontcare = S('i', UA("don't care", 'do not care'))
    it_dontcare = S('it', UA('does not matter', "don't matter", "doesn't matter"))
    go_anyway = S(UA(i_dontcare, it_dontcare), UA('how', 'which way', 'which route'))

    by_dontcare = UA('no matter how', 'any way possible', 'any possible way', 'by any means')
    vehicle_other = UA('metro', 'sub', 'coach', 'tram', 'underground', 'cable car', 'rail', 'railway', 'ferry', 'boat', 'monorail')
    vehicle = UA('bus', 'train', 'tube', 'subway', vehicle_other)
    by_vehicle = S('by', vehicle)

    go_by = S(want, 'to', A(S(A('go', 'travel'), O('there')), 'get there'), A((by_vehicle, 0.8), by_dontcare))

    go = A((go_by, 0.8), go_anyway)


    # weather
    weather_pref_p = UA('can you tell me', 'could you tell me', 'tell me', 'i would like to know', "i'd like to know",
                        'i want to know', )
    weather_pref_q_for = UA('what is', "what's")
    weather_pref_q_in = 'what will be'
    weather_pref_q = A((weather_pref_q_for, 3), (weather_pref_q_in, 1))
    weather_pref_rich = UA(weather_pref_p, weather_pref_q, S(weather_pref_p, weather_pref_q))
    weather_pref_poor = UA(weather_pref_q, S(weather_pref_p, weather_pref_q))
    weather_subject_forecast = UA('weather', 'forecast', 'weather forecast')
    weather_subject_like = 'weather like'
    weather_forecast = S(weather_pref_rich, 'the', weather_subject_forecast)
    weather_like = S(weather_pref_poor, 'the', weather_subject_like)
    weather_plain = UA(weather_forecast, weather_like)
    weather_forecast_place = S(weather_forecast, O(S('for', UA(city, state))))
    weather_like_place = S(weather_like, O(S('in', UA(city, state))))
    weather_forecast_time = S(weather_forecast, O(UA('for tomorrow', 'for today', 'in the afternoon')))
    weather_like_time = S(weather_like, O(UA('in the afternoon')))
    weather = UA(weather_plain, weather_forecast_place, weather_forecast_time, weather_like_place, weather_like_time)


    # additional questions

    question_transfers = UA(S('how many transfers', O('are there')), S(O('tell me the'), 'number of transfers'))
    when = 'when'
    reg = UA('does', 'will')
    subject = A(('it', 0.7), 'the bus', 'the train')
    noun_reg = UA('arrive', 'depart', 'go', 'leave')
    noun_cur = UA('arriving', 'departing', 'going', 'leaving')
    noun_sub = UA('arrival', 'departure', 'departure time', 'arrival time')
    question_reg = S(when, reg, subject, noun_reg)
    question_cur = S(when, 'is', subject, noun_cur)
    question_sub1 = S(when, 'is the', noun_sub)
    question_sub2 = S(UA("i'd like", 'i would like', 'i want'), 'to know the', noun_sub)
    question_sub3 = S(O('tell me', 0.2), UA("what's", 'what is'), 'the', noun_sub)
    question_sub = UA(question_sub1, question_sub2, question_sub3)

    add_questions = UA(question_reg, question_cur, question_sub, question_transfers)


    # other
    negate = S(UA("i don't", 'i do not'),UA('need', 'wish', 'want', 'care'))
    other_n_boost = UA('help', 'yes', 'no', 'sure', 'yeah', 'hello', 'hint', 'nah', 'hi', 'bye', 'good bye',
                       'thank you','thanks', 'help me', 'find a connection', "i'm looking for a connection")

    root = UA(from_0_to, a_conneciton, go, weather, location, add_questions, other_n_boost)

    return root


def generate(n, method):
    """ Generates the training data with grammar
    :param n: number of utterances to be generated
    :param method: type of method: unique or as given by the grammar.
    """
    random.seed(1)
    timestamp = datetime.now()

    print 'Sampling method:', method

    if method == 'uniq':
        save_data('./gen_data/train.unique.gen.txt', GrammarGen(grammar()).sample_uniq(n))
    elif method == 'test':
        sample = GrammarGen(grammar()).sample(n)
        for s in sample:
            print s
    else:
        save_data('./gen_data/train.regular.gen.txt', GrammarGen(grammar()).sample(n))

    print 'Sampling took ' + str(datetime.now() - timestamp)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Training data grammar generator')
    parser.add_argument('-n', default=n_samples, type=int, help='generated sentences count (default: %d)' % n_samples)
    parser.add_argument('-m', '--method', default=default_method, type=str, help='method of generating (default: %s)' % default_method)
    args = parser.parse_args()

    generate(args.n, args.method)