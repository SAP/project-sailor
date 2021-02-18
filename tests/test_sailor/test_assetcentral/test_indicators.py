class TestIndicatorSet:
    def test_get_name_mapping(self, make_indicator_set):
        indicator_set = make_indicator_set(categoryID=['id1', 'id2', 'id3'],
                                           indicatorGroupName=['group1', 'group2', 'group3'],
                                           indicatorName=['name1', 'name2', 'name3'])
        expected = {'b1803e128a8f9acf95ecb9089ca06a2bd92502b6b2a665207a51fe07b3e49f15': ('id1', 'group1', 'name1'),
                    '7922bba7c892bae3bc1da05df2754f01d4d347ee76fefff5e45a5ab5f8ec2a89': ('id2', 'group2', 'name2'),
                    '5318462fee71c0179a0c34d38ef23c21c89c1d35121848a2f4a2c3c700033752': ('id3', 'group3', 'name3')}

        actual = indicator_set._unique_id_to_names()

        assert actual == expected

    def test_get_id_mapping(self, make_indicator_set):
        indicator_set = make_indicator_set(categoryID=['id1', 'id2', 'id3'],
                                           pstid=['group1', 'group2', 'group3'],
                                           propertyId=['name1', 'name2', 'name3'])
        expected = {'1bbf466caa2c11f861f2341841f6113316964ae608f3d01848869706c40a3830': ('id1', 'group1', 'name1'),
                    '4781e1c76ae58a33fd3a049871bc8d2808d30eef5300c7e5b0fcd182476393c1': ('id2', 'group2', 'name2'),
                    '0bffa941a7a24ee72a23d294eba056cdd18ce731a68e0701856cc042aa449649': ('id3', 'group3', 'name3')}

        actual = indicator_set._unique_id_to_constituent_ids()

        assert actual == expected
