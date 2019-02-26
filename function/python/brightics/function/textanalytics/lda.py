from brightics.common.repr import BrtcReprBuilder, strip_margin, pandasDF2MD, dict2MD
from brightics.function.utils import _model_dict
from brightics.common.groupby import _function_by_group
from brightics.common.utils import check_required_parameters
from brightics.function.validation import raise_runtime_error
from brightics.common.validation import validate, greater_than_or_equal_to, less_than_or_equal_to, greater_than

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np
import pandas as pd


def lda(table, group_by=None, **params):
    check_required_parameters(_lda, params, ['table'])
    if group_by is not None:
        return _function_by_group(_lda, table, group_by=group_by, **params)
    else:
        return _lda(table, **params)


def _lda(table, input_col, num_voca=1000, num_topic=3, num_topic_word=3, max_iter=20, learning_method='online', learning_offset=10., random_state=None):
    param_validation_check = [greater_than_or_equal_to(num_voca, 2, 'num_voca'),
                              greater_than_or_equal_to(num_topic, 2, 'num_topic'),
                              greater_than_or_equal_to(num_topic_word, 2, 'num_topic_word'),
                              less_than_or_equal_to(num_topic_word, num_voca, 'num_topic_word'),
                              greater_than_or_equal_to(max_iter, 1, 'max_iter'),
                              greater_than(learning_offset, 1.0, 'learning_offset')]
    
    validate(*param_validation_check)
    
    corpus = table[input_col]
    tf_vectorizer = CountVectorizer(max_df=0.95, min_df=2, max_features=num_voca, stop_words='english')
    term_count = tf_vectorizer.fit_transform(corpus)
    tf_feature_names = tf_vectorizer.get_feature_names()

    if learning_method == 'online':
        lda_model = LatentDirichletAllocation(n_components=num_topic, max_iter=max_iter, learning_method=learning_method, learning_offset=learning_offset, random_state=random_state).fit(term_count)
    elif learning_method == 'batch':
        lda_model = LatentDirichletAllocation(n_components=num_topic, max_iter=max_iter, learning_method=learning_method, random_state=random_state).fit(term_count)
    else:
        raise_runtime_error("Please check 'learning_method'.")
    
    topic_model = pd.DataFrame([])
    topic_idx_list = []
    voca_weights_list = []
    for topic_idx, weights in enumerate(lda_model.components_):
        topic_idx_list.append("Topic {}".format(topic_idx))
        pairs = []
        for term_idx, value in enumerate(weights):
            pairs.append((abs(value), tf_feature_names[term_idx]))
        pairs.sort(key=lambda x: x[0], reverse=True)
        voca_weights = []
        for pair in pairs[:num_topic_word]:
            voca_weights.append("{}: {}".format(pair[1], pair[0]))
        voca_weights_list.append(voca_weights)
    topic_model['topic idx'] = topic_idx_list
    topic_model['topic vocabularies'] = voca_weights_list

    doc_topic = lda_model.transform(term_count)

    doc_classification = pd.DataFrame()
    doc_classification['documents'] = [doc for doc in corpus]
    doc_classification['top topic'] = ["Topic {}".format(doc_topic[i].argmax()) for i in range(len(corpus))]
    
    params = {
        'Input Column': input_col,
        'Number of Vocabularies': num_voca,
        'Number of Topics': num_topic,
        'Number of Terminologies': num_topic_word,
        'Iteration': max_iter,
        'Learning Method': learning_method,
    }
    
    rb = BrtcReprBuilder()
    rb.addMD(strip_margin("""# Latent Dirichlet Allocation Result"""))
    rb.addMD(strip_margin("""
    |
    |### Parameters
    |
    | {display_params}
    |
    |### Topic Model
    |
    |{topic_model}
    |
    |### Documents Classification
    |
    |{doc_classification}
    |
    """.format(display_params=dict2MD(params), topic_model=pandasDF2MD(topic_model, num_rows=num_topic + 1), doc_classification=pandasDF2MD(doc_classification, num_rows=len(corpus) + 1))))
    
    model = _model_dict('lda')
    model['topic_model'] = topic_model
    model['documents_classification'] = doc_classification
    model['_repr_brtc_'] = rb.get()

    return {'model' : model}
