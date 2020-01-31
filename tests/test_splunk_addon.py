# -*- coding: utf-8 -*-
import pytest
from flaky import flaky

def test_splunk_connection(testdir,splunk_server):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    testdir.makepyfile("""
        def test_connection_splunk(splunk_search_util):
            search = "search (index=_internal) | head 5"

             # run search
            result = splunk_search_util.checkQueryCountIsGreaterThanZero(
                search,
                interval=1, retries=1)
            assert result
    """)

    # run pytest with the following cmd args
    result = testdir.runpytest(
        '--splunk_app=tests/addons/TA_fiction',
        f'--splunk_host={splunk_server[0]}',
        f'--splunk_port={splunk_server[1]}',
        '--splunk_password=Changed@11',
        '-v'
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_connection_splunk PASSED*',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


@flaky(max_runs=5, min_passes=1)
def test_splunk_app_fiction(testdir,splunk_server):
    """Make sure that pytest accepts our fixture."""

    testdir.makepyfile("""
        from pytest_splunk_addon.standard_lib.addon_basic import Basic
        class Test_App(Basic):
            def empty_method():
                pass
            
    """)


    # run pytest with the following cmd args
    result = testdir.runpytest(
        '--splunk_app=/Users/rfaircloth/PycharmProjects/pytest-splunk-addon/tests/addons/TA_fiction',
        f'--splunk_host={splunk_server[0]}',
        f'--splunk_port={splunk_server[1]}',
        '--splunk_password=Changed@11',
        '--no-flaky-report',
        '-v',
    )

    #'*test_fields*splunkd*EXTRACT-two*PASSED*',
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*test_basic_sourcetypes*splunkd*PASSED*',
        '*test_basic_eventtype*splunkd*PASSED*',
        '*test_fields*splunkd*EXTRACT-one*PASSED*',

        '*test_fields*splunkd*FIELDALIAS-one*PASSED*'
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_splunk_app_broken_sourcetype(testdir,splunk_server):
    """Make sure that pytest accepts our fixture."""

    testdir.makepyfile("""
        from pytest_splunk_addon.standard_lib.addon_basic import Basic
        class Test_App(Basic):
            def empty_method():
                pass

    """)

    # run pytest with the following cmd args
    result = testdir.runpytest(
        '--splunk_app=/Users/rfaircloth/PycharmProjects/pytest-splunk-addon/tests/addons/TA_broken_sourcetype',
        f'--splunk_host={splunk_server[0]}',
        f'--splunk_port={splunk_server[1]}',
        '--splunk_password=Changed@11',
        '-v'
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*test_basic_sourcetypes*notvalid*FAILED*',
        '*test_fields*notvalid::EXTRACT-one* SKIPPED*',
    ])

    # The test suite should fail as this is a negative test
    assert result.ret != 0


def test_help_message(testdir):
    result = testdir.runpytest(
        '--help',
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'splunk-addon:',
        '*--splunk_app=*',
        '*--splunk_host=*',
        '*--splunk_port=*',
        '*--splunk_user=*',
        '*--splunk_password=*',
    ])
