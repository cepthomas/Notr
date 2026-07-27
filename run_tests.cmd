
cls
echo off

pushd tests
python -m unittest test_notr test_table
popd

