import argparse
from pathlib import Path
import subprocess
from io import BytesIO
import hashlib
import os
import json
import zipfile
import tempfile
import shutil
import random
from typing import Sequence

from . import far4_tools
from . import l0_dec_enc

def get_sha1_hex(data) -> str:
    m = hashlib.sha1()
    m.update(data)
    return m.hexdigest()


HASHES = (
    '5a2da2be54bc8de6be3321652608b1437127e1fa',
    '02d81fc95f1dbde4369a6db9109df67a6bc6285f',
    '841a3e4b48bc23a66e6ffb7d47ce02abda0df680',
    '78feb1d66a26d3945eb26a5f6168c444be693e75',
    '29afff1b4a7126a4d634ee75128e1ec8609f875f',
    '500707bf0f7f30d933d5a84302ec599acf9ce392',
    '1c066544d5c6963721f3d40b900b6ae327c77905',
    'ea4158ab4bbb7807f5d6c4cc904ef2e664fb5b27',
    'a78d1ea8b64de4c8080ccd1aa0cdbee58dea4470',
    'a3b8e8eb9f232eeb46f8618ec6d8438e93f9c093',
    '7ec70985949ed578a72278be93b7cc19e7390a69',
    '9930954371bc9d0ff6ac33ea686f8252a4fe3bf3',
    '8cad0af58dea539b6c901757e9a9bb2f9a2c1cc4',
    '4046c06e4ddf2d6c6ce90b34208b4ff30e1be2bd',
    '857d0a083e86b1c460aa7a0cdc3aeba6a6daf1d5',
    '335255daaa75ee85eeab8558d015a359e22c3180',
    'bbd04b104e2229312531d8b282a817ae9b7023fe',
    '9cd69ec5dbe8340f4bc55d3be5dc1b3f76e15815',
    '05ca495561fc547084b281831d209e5dcb097e7d',
    '05b92e1067e0ced2b642987271e6e11e6e432735',
    '34569eec9cbd4e92a200ca81af1ec3d4bbc987b2',
    '60f66d08700e09439571af23840b60fbb9ef0fde',
    'f68d18c8f5e442db8b9556a5c74f79a748702c9e',
    '9d1c1434d5572ca43fc8345020490edc56b5527a',
    '491d1e7f8795d4d8ac018533071bf08ac42d8f11',
    '756552005925b1ed8f89e44d40194687427e1130',
    '35013f0caa22dee94774308fa9cb8e49e4a0f213',
    '8486e0cdad3bf4b6a1cb1e5b670f5072d2c2524f',
    '45818878326d57dd9735f4290bcbdff79915ed8b',
    'c144fda2a0236973bf65082029c5060c79d4b465',
    '484effff879ec247ad2b9ac729cfd22e07e535bf',
    '67fd27388908394e73978ff9a4c723926ff328cb',
    'd40657e4e0af36acbc470d050e17fdea4ce83ce3',
    '2040572907f64001b5a96e44af4640120e61b49b',
    '0036b09d78cbed3d717ec37442401121d3995dad',
    'dbd5b1cf0d8ca7384373a7389aa9a8b8dd223c6a',
    'cb348f86f7e00fbb1ac05cfd5622f108e4f46490',
    'aa8de32efbcad9140a969b0988558dec1fe6a90a',
    '05157d16524f4b3a35e863a55f395e7a9017ba5c',
    'e8f2b7058b64dafab650c55e20dfb174b3b9237e',
    'cb1faef12dcb0fe680ceb0672e91ce442a4c23ae',
    '9575e11dbf43bedf68fc45c876c609a585b508bb',
    '0c460558bc14760cc4543495410a072377b69d34',
    'e3b89743342871a7d2c29751e4fca7d058a8146a',
    '6be3809731c0293b8cdb4643c4a357f94561cbc6',
    'a133216e6f5e3121fd9955ba84d4ebab44e52bef',
    '968142f12637d8d80bc07448a660072d52c0bdbe',
    '1be9448e568cfd576f2f6253809d657f126f8bc1',
    '73490d042de423da1c99947dbd9e167daebf90ec',
    '386c7e225ff6b8aa782071d1b219fc144c7e6fcb',
    '1409b9f1df98542bb46c4d36e3d357a35990c1e9',
    'a52df928d9bf52fec36eeff496f01470c68f1cb0',
    '4f35fc3b787bb055783460b7bf90ba1e08b2d4f0',
    '6024c33bcfeec2c8646bf0333ebc85f3c5ed1b35',
    '0180f1276188c29377c61f88d2d0881636aead8a',
    '64a3bacf1c028fff59c114d0ebc3503f3280b9d5',
    '015b0d32099cab30bdacc2dbcfd65e6ac609590a',
    '65174045d5c22f42410ff1e8b63cbb002df73530',
    '96146a34dd63775944cc4aa81ecbd9a8c4bb4f48',
    'dcfaa613d02f33b25056772bd327e0ac5e51132a',
    'd27cdfda51b7719fc4418aa08fcdfad7aeb218b3',
    '10b07f85481a9b6b8ef2e4902cf07a60817c1598',
    'a44a04aac982855fab0785d69d9a1132ca397582',
    '3ece869920429de322303c88494a3e7a6d94bcd7',
    '4b09a57a894bfaf5165649ec8b64edaf0ae83dd4',
    'a42f2800c739971fefbe71743b41f3e16a0fc6f0',
    'fa17d15757092fbd0ef84ccc9b17ccca7aaef3c7',
    'd1d6bcd2403be25059a43df9805bed468a04aa15',
    'ea08a442234ec23e2f19eb49f3f24ada4b0a28e6',
    '0ece809370a03d9bb0247f2365a0513eeb41ade6'
)

LBP1_SLOT_COORDINATES = (
    ('USER_CREATED_STORED_LOCAL:77', (-0.8888866, 0.30699086, -0.34005484, 0.0)),
    ('USER_CREATED_STORED_LOCAL:44', (-0.8763887, -0.40167686, -0.26570392, 0.0)),
    ('USER_CREATED_STORED_LOCAL:11', (-0.09783502, 0.025761006, 0.99486923, 0.0)),
    ('USER_CREATED_STORED_LOCAL:81', (0.5242757, -0.5701827, 0.6324766, 0.0)),
    ('USER_CREATED_STORED_LOCAL:48', (-0.91347873, -0.25022894, -0.3208459, 0.0)),
    ('USER_CREATED_STORED_LOCAL:15', (0.8303515, 0.5512984, -0.08115804, 0.0)),
    ('USER_CREATED_STORED_LOCAL:52', (-0.6752077, -0.6518117, -0.34530583, 0.0)),
    ('USER_CREATED_STORED_LOCAL:19', (0.47776696, 0.87838393, -0.013427999, 0.0)),
    ('USER_CREATED_STORED_LOCAL:56', (-0.5452938, -0.13882895, -0.82666874, 0.0)),
    ('USER_CREATED_STORED_LOCAL:23', (0.512454, 0.366131, 0.776749, 0.0)),
    ('USER_CREATED_STORED_LOCAL:60', (0.95858824, -0.18041405, 0.22036205, 0.0)),
    ('USER_CREATED_STORED_LOCAL:27', (0.98948795, 0.023391997, 0.14271098, 0.0)),
    ('USER_CREATED_STORED_LOCAL:64', (0.46892294, -0.76497185, -0.44150794, 0.0)),
    ('USER_CREATED_STORED_LOCAL:31', (0.3719329, 0.50006884, 0.7820467, 0.0)),
    ('USER_CREATED_STORED_LOCAL:68', (-0.20356704, -0.44608912, -0.8715302, 0.0)),
    ('USER_CREATED_STORED_LOCAL:35', (-0.26347908, 0.8988393, 0.3502381, 0.0)),
    ('USER_CREATED_STORED_LOCAL:2', (0.7486169, 0.60400087, 0.27341494, 0.0)),
    ('USER_CREATED_STORED_LOCAL:72', (-0.8650643, -0.15859807, 0.47593117, 0.0)),
    ('USER_CREATED_STORED_LOCAL:39', (0.8426612, -0.19560504, -0.50165814, 0.0)),
    ('USER_CREATED_STORED_LOCAL:6', (0.4088082, -0.9105484, -0.06146103, 0.0)),
    ('USER_CREATED_STORED_LOCAL:45', (-0.93659484, -0.32658395, -0.12701596, 0.0)),
    ('USER_CREATED_STORED_LOCAL:12', (-0.4167152, -0.06320103, -0.9068374, 0.0)),
    ('USER_CREATED_STORED_LOCAL:74', (-0.47690418, -0.8752783, 0.08031403, 0.0)),
    ('USER_CREATED_STORED_LOCAL:49', (-0.95822436, -0.24382709, -0.14951406, 0.0)),
    ('USER_CREATED_STORED_LOCAL:16', (0.6335288, 0.7239608, -0.27298695, 0.0)),
    ('USER_CREATED_STORED_LOCAL:78', (-0.8180849, 0.51174086, -0.26240894, 0.0)),
    ('USER_CREATED_STORED_LOCAL:53', (-0.8629373, 0.5012612, -0.06384702, 0.0)),
    ('USER_CREATED_STORED_LOCAL:20', (0.62219197, 0.75183296, 0.21822998, 0.0)),
    ('USER_CREATED_STORED_LOCAL:57', (0.61655706, 0.18021101, -0.76640815, 0.0)),
    ('USER_CREATED_STORED_LOCAL:24', (0.98978335, -0.14198504, 0.013014005, 0.0)),
    ('USER_CREATED_STORED_LOCAL:61', (0.84370273, 0.2576859, -0.47091785, 0.0)),
    ('USER_CREATED_STORED_LOCAL:28', (0.965258, -0.047163, 0.257007, 0.0)),
    ('USER_CREATED_STORED_LOCAL:65', (-0.3769459, -0.3602679, -0.85329884, 0.0)),
    ('USER_CREATED_STORED_LOCAL:32', (-0.38784105, -0.21594504, -0.8960731, 0.0)),
    ('USER_CREATED_STORED_LOCAL:69', (-0.82691664, -0.26985687, 0.4933418, 0.0)),
    ('USER_CREATED_STORED_LOCAL:36', (-0.05115603, 0.7022214, -0.7101184, 0.0)),
    ('USER_CREATED_STORED_LOCAL:3', (0.39563915, -0.8774683, -0.2711441, 0.0)),
    ('USER_CREATED_STORED_LOCAL:73', (-0.5884999, -0.7519028, 0.29716995, 0.0)),
    ('USER_CREATED_STORED_LOCAL:40', (-0.24126509, -0.2668241, -0.93305737, 0.0)),
    ('USER_CREATED_STORED_LOCAL:7', (0.5479258, -0.82450265, -0.14132494, 0.0)),
    ('USER_CREATED_STORED_LOCAL:13', (-0.26614404, 0.79785514, -0.5409201, 0.0)),
    ('USER_CREATED_STORED_LOCAL:75', (-0.60155725, -0.7851503, 0.14720006, 0.0)),
    ('USER_CREATED_STORED_LOCAL:42', (-0.9484006, -0.20853193, -0.2388529, 0.0)),
    ('USER_CREATED_STORED_LOCAL:17', (0.754212, 0.614567, -0.231239, 0.0)),
    ('USER_CREATED_STORED_LOCAL:79', (-0.94460547, 0.32007915, -0.07259504, 0.0)),
    ('USER_CREATED_STORED_LOCAL:46', (-0.92078555, -0.31372318, -0.23180114, 0.0)),
    ('USER_CREATED_STORED_LOCAL:21', (0.8079443, 0.5790812, 0.109046035, 0.0)),
    ('USER_CREATED_STORED_LOCAL:50', (0.4321622, -0.37104517, -0.8219254, 0.0)),
    ('USER_CREATED_STORED_LOCAL:25', (0.99952567, -0.023080993, 0.020388993, 0.0)),
    ('USER_CREATED_STORED_LOCAL:54', (-0.41883606, -0.85028714, 0.31872904, 0.0)),
    ('USER_CREATED_STORED_LOCAL:29', (0.6841198, 0.72766775, -0.049796984, 0.0)),
    ('USER_CREATED_STORED_LOCAL:58', (0.17522402, -0.8983221, 0.40288207, 0.0)),
    ('USER_CREATED_STORED_LOCAL:33', (-0.4184162, -0.49700522, -0.76020634, 0.0)),
    ('USER_CREATED_STORED_LOCAL:0', (0.31077105, -0.83225715, -0.45909613, 0.0)),
    ('USER_CREATED_STORED_LOCAL:62', (0.86589384, 0.25325894, 0.4313789, 0.0)),
    ('USER_CREATED_STORED_LOCAL:37', (-0.021189002, -0.70984006, 0.70404404, 0.0)),
    ('USER_CREATED_STORED_LOCAL:4', (0.20288597, -0.9144148, -0.35026094, 0.0)),
    ('USER_CREATED_STORED_LOCAL:66', (0.11805903, 0.3125141, -0.9425482, 0.0)),
    ('USER_CREATED_STORED_LOCAL:41', (0.7592101, -0.010854001, 0.65075505, 0.0)),
    ('USER_CREATED_STORED_LOCAL:8', (0.5672089, -0.7657998, -0.30302593, 0.0)),
    ('USER_CREATED_STORED_LOCAL:70', (-0.76749134, -0.24230312, 0.5935033, 0.0)),
    ('USER_CREATED_STORED_LOCAL:76', (-0.34879893, -0.9241368, 0.15591797, 0.0)),
    ('USER_CREATED_STORED_LOCAL:43', (-0.9016544, -0.39435717, -0.17748709, 0.0)),
    ('USER_CREATED_STORED_LOCAL:10', (-0.05300901, -0.17990205, 0.9822552, 0.0)),
    ('USER_CREATED_STORED_LOCAL:80', (-0.956602, 0.193788, -0.217621, 0.0)),
    ('USER_CREATED_STORED_LOCAL:47', (-0.8799429, -0.34116998, -0.33061096, 0.0)),
    ('USER_CREATED_STORED_LOCAL:14', (-0.07221399, 0.83258086, -0.5491759, 0.0)),
    ('USER_CREATED_STORED_LOCAL:51', (-0.23641692, 0.6839048, -0.69020385, 0.0)),
    ('USER_CREATED_STORED_LOCAL:18', (0.50869703, 0.8305341, -0.22680503, 0.0)),
    ('USER_CREATED_STORED_LOCAL:55', (-0.027164994, 0.6557988, 0.7544468, 0.0)),
    ('USER_CREATED_STORED_LOCAL:22', (0.35630608, 0.3279511, 0.8749252, 0.0)),
    ('USER_CREATED_STORED_LOCAL:59', (-0.32325393, -0.12421998, 0.9381238, 0.0)),
    ('USER_CREATED_STORED_LOCAL:26', (0.9697515, -0.2230121, 0.09923604, 0.0)),
    ('USER_CREATED_STORED_LOCAL:1', (0.4628601, 0.86776716, 0.18094404, 0.0)),
    ('USER_CREATED_STORED_LOCAL:63', (0.24578999, 0.36295098, -0.8988069, 0.0)),
    ('USER_CREATED_STORED_LOCAL:30', (-0.55120695, -0.33277997, -0.7651329, 0.0)),
    ('USER_CREATED_STORED_LOCAL:5', (0.25761792, -0.9545006, -0.15020494, 0.0)),
    ('USER_CREATED_STORED_LOCAL:67', (0.24369888, 0.2274599, -0.9428005, 0.0)),
    ('USER_CREATED_STORED_LOCAL:34', (-0.261681, -0.104449, -0.959486, 0.0)),
    ('USER_CREATED_STORED_LOCAL:9', (-0.172129, -0.322175, 0.9309, 0.0)),
    ('USER_CREATED_STORED_LOCAL:71', (-0.80561, -0.125551, 0.57899, 0.0)),
    ('USER_CREATED_STORED_LOCAL:38', (-0.7321999, 0.41059193, 0.54341286, 0.0))
)

LBP1_SLOT_TEMPLATE = """{
    "id": "USER_CREATED_STORED_LOCAL:0",
    "root": {
      "value": "6d0642c0f5452258b1d44d5e9d69269b9b1405ac",
      "type": "LEVEL"
    },
    "icon": {
      "value": "6d0642c0f5452258b1d44d5e9d69269b9b1405ab",
      "type": "TEXTURE"
    },
    "location": [
      0.31077105,
      -0.83225715,
      -0.45909613,
      0.0
    ],
    "authorID": "",
    "authorName": "",
    "translationTag": "",
    "name": "mods 2 levels",
    "description": "",
    "primaryLinkLevel": "NONE",
    "group": "NONE",
    "initiallyLocked": false,
    "shareable": false,
    "backgroundGUID": null,
    "developerLevelType": "MAIN_PATH",
    "gameProgressionState": "FIRST_LEVEL_COMPLETED"
}"""

LBP3_SLOT_COORDINATES = (
    ('USER_CREATED_STORED_LOCAL:7', (0.5248221, -0.8119892, -0.25541207, 0.0)),
    ('USER_CREATED_STORED_LOCAL:40', (-0.31536397, -0.19392496, -0.9289449, 0.0)),
    ('USER_CREATED_STORED_LOCAL:73', (-0.5378789, -0.74035084, 0.40319592, 0.0)),
    ('USER_CREATED_STORED_LOCAL:11', (0.053192973, 0.025618987, 0.99825555, 0.0)),
    ('USER_CREATED_STORED_LOCAL:44', (-0.91303694, -0.38422298, -0.13687998, 0.0)),
    ('USER_CREATED_STORED_LOCAL:77', (-0.9226437, 0.3269559, -0.20451994, 0.0)),
    ('USER_CREATED_STORED_LOCAL:32', (-0.55164087, -0.21482195, -0.8059429, 0.0)),
    ('USER_CREATED_STORED_LOCAL:65', (-0.48730212, -0.3744961, -0.78885317, 0.0)),
    ('USER_CREATED_STORED_LOCAL:3', (0.3390612, -0.8742445, -0.3474682, 0.0)),
    ('USER_CREATED_STORED_LOCAL:36', (-0.11301704, 0.8784243, -0.4643252, 0.0)),
    ('USER_CREATED_STORED_LOCAL:69', (-0.75691617, -0.24991706, 0.60383713, 0.0)),
    ('USER_CREATED_STORED_LOCAL:23', (0.62834, 0.34902, 0.695251, 0.0)),
    ('USER_CREATED_STORED_LOCAL:56', (-0.690833, -0.132761, -0.710721, 0.0)),
    ('USER_CREATED_STORED_LOCAL:27', (0.9994955, 0.025358012, -0.019124009, 0.0)),
    ('USER_CREATED_STORED_LOCAL:60', (0.97940934, -0.19448908, 0.05414302, 0.0)),
    ('USER_CREATED_STORED_LOCAL:15', (0.8138356, 0.53664476, -0.22289892, 0.0)),
    ('USER_CREATED_STORED_LOCAL:48', (-0.95851827, -0.23114106, -0.16678305, 0.0)),
    ('USER_CREATED_STORED_LOCAL:81', (0.83252716, -0.5501321, 0.06521601, 0.0)),
    ('USER_CREATED_STORED_LOCAL:19', (0.46152917, 0.8812123, -0.102253035, 0.0)),
    ('USER_CREATED_STORED_LOCAL:52', (-0.7317929, -0.6429439, -0.22605798, 0.0)),
    ('USER_CREATED_STORED_LOCAL:39', (0.74562633, -0.1843541, -0.6403553, 0.0)),
    ('USER_CREATED_STORED_LOCAL:72', (-0.7775172, -0.13172904, 0.6149101, 0.0)),
    ('USER_CREATED_STORED_LOCAL:10', (0.11623898, -0.19960797, 0.9729569, 0.0)),
    ('USER_CREATED_STORED_LOCAL:43', (-0.9172905, -0.39529023, -0.04820503, 0.0)),
    ('USER_CREATED_STORED_LOCAL:76', (-0.2941059, -0.9257966, 0.23749189, 0.0)),
    ('USER_CREATED_STORED_LOCAL:14', (-0.09560399, 0.9576028, -0.27176595, 0.0)),
    ('USER_CREATED_STORED_LOCAL:31', (0.51312673, 0.5000767, 0.69758457, 0.0)),
    ('USER_CREATED_STORED_LOCAL:64', (0.39728823, -0.7529645, -0.5246013, 0.0)),
    ('USER_CREATED_STORED_LOCAL:2', (0.777997, 0.610497, 0.148371, 0.0)),
    ('USER_CREATED_STORED_LOCAL:35', (-0.20835088, 0.8911815, 0.4029708, 0.0)),
    ('USER_CREATED_STORED_LOCAL:68', (-0.3145371, -0.38218415, -0.8689083, 0.0)),
    ('USER_CREATED_STORED_LOCAL:6', (0.37352908, -0.91859126, -0.12909803, 0.0)),
    ('USER_CREATED_STORED_LOCAL:55', (0.09271405, 0.6559274, 0.74910843, 0.0)),
    ('USER_CREATED_STORED_LOCAL:26', (0.96940535, -0.2348231, -0.07149502, 0.0)),
    ('USER_CREATED_STORED_LOCAL:59', (-0.18722709, -0.12533206, 0.97428846, 0.0)),
    ('USER_CREATED_STORED_LOCAL:30', (-0.69867504, -0.32301602, -0.63836807, 0.0)),
    ('USER_CREATED_STORED_LOCAL:47', (-0.92981476, -0.31520292, -0.18997796, 0.0)),
    ('USER_CREATED_STORED_LOCAL:80', (-0.97560966, 0.20564793, -0.076776974, 0.0)),
    ('USER_CREATED_STORED_LOCAL:18', (0.4924268, 0.8124397, -0.3121819, 0.0)),
    ('USER_CREATED_STORED_LOCAL:51', (-0.316601, 0.852023, -0.416918, 0.0)),
    ('USER_CREATED_STORED_LOCAL:22', (0.4763743, 0.3434002, 0.8094095, 0.0)),
    ('USER_CREATED_STORED_LOCAL:71', (-0.6971328, -0.13262197, 0.7045688, 0.0)),
    ('USER_CREATED_STORED_LOCAL:9', (-0.041708987, -0.32910192, 0.9433728, 0.0)),
    ('USER_CREATED_STORED_LOCAL:42', (-0.9766321, -0.20016304, -0.078259006, 0.0)),
    ('USER_CREATED_STORED_LOCAL:75', (-0.5762558, -0.7797927, 0.2446479, 0.0)),
    ('USER_CREATED_STORED_LOCAL:13', (-0.29595807, 0.92773426, -0.22741605, 0.0)),
    ('USER_CREATED_STORED_LOCAL:46', (-0.9491289, -0.30334398, -0.08447899, 0.0)),
    ('USER_CREATED_STORED_LOCAL:63', (-0.54199266, 0.41537574, -0.7305525, 0.0)),
    ('USER_CREATED_STORED_LOCAL:1', (0.4678959, 0.87881374, 0.09359398, 0.0)),
    ('USER_CREATED_STORED_LOCAL:34', (-0.4477672, -0.08849304, -0.88976043, 0.0)),
    ('USER_CREATED_STORED_LOCAL:67', (-0.5598222, 0.5301392, -0.63682926, 0.0)),
    ('USER_CREATED_STORED_LOCAL:5', (0.17382409, -0.95636547, -0.23484112, 0.0)),
    ('USER_CREATED_STORED_LOCAL:38', (-0.9445418, -0.050015993, 0.32455993, 0.0)),
    ('USER_CREATED_STORED_LOCAL:25', (0.98970294, -0.018697998, -0.14190999, 0.0)),
    ('USER_CREATED_STORED_LOCAL:58', (0.23542188, -0.9010166, 0.3643428, 0.0)),
    ('USER_CREATED_STORED_LOCAL:29', (0.6593018, 0.73002976, -0.17993794, 0.0)),
    ('USER_CREATED_STORED_LOCAL:62', (0.9250968, 0.25169894, 0.28432995, 0.0)),
    ('USER_CREATED_STORED_LOCAL:79', (-0.94591147, 0.31479314, 0.078466035, 0.0)),
    ('USER_CREATED_STORED_LOCAL:17', (0.7134027, 0.60602474, -0.35183886, 0.0)),
    ('USER_CREATED_STORED_LOCAL:50', (0.28622508, -0.36067012, -0.8876893, 0.0)),
    ('USER_CREATED_STORED_LOCAL:21', (0.813017, 0.58145, -0.030317, 0.0)),
    ('USER_CREATED_STORED_LOCAL:54', (-0.35759908, -0.8473742, 0.39253008, 0.0)),
    ('USER_CREATED_STORED_LOCAL:8', (0.5248129, -0.74482983, -0.41206792, 0.0)),
    ('USER_CREATED_STORED_LOCAL:41', (0.85473895, -0.010594999, 0.5189499, 0.0)),
    ('USER_CREATED_STORED_LOCAL:74', (-0.4347799, -0.88440377, 0.16969496, 0.0)),
    ('USER_CREATED_STORED_LOCAL:12', (-0.5848139, -0.03537499, -0.81039584, 0.0)),
    ('USER_CREATED_STORED_LOCAL:45', (-0.9418622, -0.33555508, 0.017276004, 0.0)),
    ('USER_CREATED_STORED_LOCAL:78', (-0.844277, 0.521593, -0.123033, 0.0)),
    ('USER_CREATED_STORED_LOCAL:0', (0.228, -0.817, -0.53, 0.0)),
    ('USER_CREATED_STORED_LOCAL:33', (-0.56181186, -0.49182987, -0.6651848, 0.0)),
    ('USER_CREATED_STORED_LOCAL:66', (-0.4388629, 0.5225128, -0.73101276, 0.0)),
    ('USER_CREATED_STORED_LOCAL:4', (0.12523201, -0.9050611, -0.40642506, 0.0)),
    ('USER_CREATED_STORED_LOCAL:37', (0.08895204, -0.7097124, 0.6988534, 0.0)),
    ('USER_CREATED_STORED_LOCAL:70', (-0.6758379, -0.25107795, 0.6929669, 0.0)),
    ('USER_CREATED_STORED_LOCAL:24', (0.9767195, -0.14132607, -0.16138807, 0.0)),
    ('USER_CREATED_STORED_LOCAL:57', (0.48501617, 0.19240208, -0.8530773, 0.0)),
    ('USER_CREATED_STORED_LOCAL:28', (0.99357015, -0.06181501, 0.09485401, 0.0)),
    ('USER_CREATED_STORED_LOCAL:61', (0.7533981, 0.26474202, -0.6019161, 0.0)),
    ('USER_CREATED_STORED_LOCAL:16', (0.58721685, 0.7002269, -0.40602794, 0.0)),
    ('USER_CREATED_STORED_LOCAL:49', (-0.9693676, -0.2455579, 0.005259998, 0.0)),
    ('USER_CREATED_STORED_LOCAL:20', (0.64410996, 0.7576859, 0.10504498, 0.0)),
    ('USER_CREATED_STORED_LOCAL:53', (-0.8620861, 0.50048107, 0.07953801, 0.0))
)

LBP3_SLOT_TEMPLATE = """{
    "id": "USER_CREATED_STORED_LOCAL:7",
    "root": {
      "value": "5b6227e14a496fc34cc484ee200fc86142a468f6",
      "type": "LEVEL"
    },
    "adventure": null,
    "icon": {
      "value": "6d0642c0f5452258b1d44d5e9d69269b9b1405ab",
      "type": "TEXTURE"
    },
    "location": [
      0.5248221,
      -0.8119892,
      -0.25541207,
      0.0
    ],
    "authorID": "",
    "authorName": "",
    "translationTag": "",
    "name": "mods 2 levels",
    "description": "",
    "primaryLinkLevel": "NONE",
    "group": "NONE",
    "initiallyLocked": false,
    "shareable": false,
    "backgroundGUID": null,
    "developerLevelType": "MAIN_PATH",
    "planetDecorations": null,
    "labels": [],
    "collectabubblesRequired": [],
    "collectabubblesContained": [],
    "isSubLevel": false,
    "minPlayers": 1,
    "maxPlayers": 4,
    "moveRecommended": false,
    "crossCompatible": false,
    "showOnPlanet": true,
    "livesOverride": 0,
    "enforceMinMaxPlayers": false,
    "gameMode": 0,
    "isGameKit": false,
    "entranceName": "",
    "originalSlotID": "NONE",
    "customBadgeSize": 1,
    "localPath": "",
    "thumbPath": ""
}"""


TEMPLATE_LEVEL = Path('custom_cheats','littlebigplanet_3','mod_installer','LBP1_BIN_ARRAY.json').read_text()

LEVEL_ICO_TEX =  Path('custom_cheats','littlebigplanet_3','mod_installer','image.tex').read_bytes()

LEVEL_ICO_TEX_HASH = get_sha1_hex(LEVEL_ICO_TEX)

JSONINATOR_ARGS = ('java','-jar',Path('custom_cheats','littlebigplanet_3','mod_installer','jsoninator.jar'))
test_result = subprocess.run(JSONINATOR_ARGS,capture_output=True)

if test_result.returncode:
    raise Exception(f'something went wrong with jsoninator... {test_result.stderr}')

# for hash in HASHES:
    # assert hash in TEMPLATE_LEVEL


def install_mods_to_bigfart(bigfart: Path, mod_files: Sequence[Path],/,*,install_plans: bool = True, is_ps4_level_backup: bool = False):
    with tempfile.TemporaryDirectory() as temp_dir:
        os.mkdir(Path(temp_dir,'mod_dump'))
        
        Path(temp_dir,'mod_dump',LEVEL_ICO_TEX_HASH + '.tex').write_bytes(LEVEL_ICO_TEX)

        if is_ps4_level_backup:
            bigfart.write_bytes(l0_dec_enc.decrypt_ps4_l0(bigfart.read_bytes()))
            # far4_tools.extract_far4(bigfart,Path(temp_dir,'mod_dump'))
            # alresdy_bin, = {x for x in Path(temp_dir,'mod_dump').iterdir() if x.suffix == '.bin'}
            # shutil.rmtree(Path(temp_dir,'mod_dump'))
            # os.mkdir(Path(temp_dir,'mod_dump'))
        
        for mod_file in mod_files:
            with zipfile.ZipFile(mod_file, 'r') as zip_ref:
                if zip_ref.getinfo('data.farc').file_size > 99_000_000:
                    raise Exception('mod file too big')
                zip_ref.extract('data.farc',temp_dir)

            far4_tools.extract_far4(Path(temp_dir,'data.farc'),Path(temp_dir,'mod_dump'))
        
        if install_plans:
            plan_hashes = [get_sha1_hex(file.read_bytes()) for file in Path(temp_dir,'mod_dump').iterdir() if file.suffix == '.plan'] 
            plan_hashes = [plan_hashes[i:i+len(HASHES)] for i in range(0, len(plan_hashes), len(HASHES))]
            
            for plan_hash_chunk in plan_hashes:
                new_lvl = TEMPLATE_LEVEL
                for index, hash in enumerate(HASHES):
                    try:
                        new_lvl = new_lvl.replace(hash,plan_hash_chunk[index])
                    except IndexError:
                        new_lvl = new_lvl.replace(hash,plan_hash_chunk[0])
                
                Path(temp_dir,'temp_lvl_json.json').write_text(new_lvl)
                subprocess.run(JSONINATOR_ARGS + (Path(temp_dir,'temp_lvl_json.json'),Path(temp_dir,'temp_lvl_json.bin')),capture_output = True, shell=False)
                bin_hash = get_sha1_hex(Path(temp_dir,'temp_lvl_json.bin').read_bytes()) + '.bin'
                
                Path(temp_dir,'mod_dump',bin_hash).write_bytes(Path(temp_dir,'temp_lvl_json.bin').read_bytes())


        bin_level_hashes = [get_sha1_hex(x.read_bytes()) for x in Path(temp_dir,'mod_dump').iterdir() if x.suffix == '.bin']
        save_key = far4_tools.extract_far4(bigfart,Path(temp_dir,'mod_dump'))
        
        
        if is_ps4_level_backup:
            slt_file, = {x for x in Path(temp_dir,'mod_dump').iterdir() if x.suffix == '.slt'}
            subprocess.run(JSONINATOR_ARGS + (Path(temp_dir,'mod_dump',slt_file),Path(temp_dir,'slt_dump.json')),capture_output = True, shell=False)
            slt_json = json.loads(Path(temp_dir,'slt_dump.json').read_text())
            #os.remove(alresdy_bin)
            slt_json["resource"]["slots"][0]["name"] = 'mods 2 levels'
            slt_json["resource"]["slots"][0]["icon"]["value"] = LEVEL_ICO_TEX_HASH
            for bin_level_hash in bin_level_hashes:
                slt_json["resource"]["slots"][0]["root"]["value"] = bin_level_hash
            
            Path(temp_dir,'slt_dump.json').write_text(json.dumps(slt_json))
            subprocess.run(JSONINATOR_ARGS + (Path(temp_dir,'slt_dump.json'),Path(temp_dir,'mod_dump',slt_file)),capture_output = True, shell=False)
            
            far4_tools.pack_far4(Path(temp_dir,'mod_dump'),bigfart,save_key,bytes.fromhex(get_sha1_hex(Path(temp_dir,'mod_dump',slt_file).read_bytes())))
            
            bigfart.write_bytes(l0_dec_enc.encrypt_ps4_l0(bigfart.read_bytes()))
        else:
            bpr_file, = {x for x in Path(temp_dir,'mod_dump').iterdir() if x.suffix == '.bpr'}


            if save_key.is_lbp3_revision:
                slots_coords, slot_template = LBP3_SLOT_COORDINATES,json.loads(LBP3_SLOT_TEMPLATE)
            else:
                slots_coords, slot_template = LBP1_SLOT_COORDINATES,json.loads(LBP1_SLOT_TEMPLATE)

            subprocess.run(JSONINATOR_ARGS + (Path(temp_dir,'mod_dump',bpr_file),Path(temp_dir,'bpr_dump.json')),capture_output = True, shell=False)
            bpr_json = json.loads(Path(temp_dir,'bpr_dump.json').read_text())


            for bin_level_hash in bin_level_hashes:
                for new_id,slot_coord in slots_coords:
                    if new_id not in bpr_json["resource"]["myMoonSlots"]:
                        break
                else:
                    raise Exception('savefile does not have any free slots')

                slot_template["location"] = slot_coord
                slot_template["id"] = new_id
                slot_template["root"]["value"] = bin_level_hash
                
                bpr_json["resource"]["myMoonSlots"] |= {new_id:slot_template}
                
                Path(temp_dir,'bpr_dump.json').write_text(json.dumps(bpr_json))
                
                subprocess.run(JSONINATOR_ARGS + (Path(temp_dir,'bpr_dump.json'),Path(temp_dir,'mod_dump',bpr_file)),capture_output = True, shell=False)
                

                
                bpr_hash = bytes.fromhex(get_sha1_hex(Path(temp_dir,'mod_dump',bpr_file).read_bytes()))
                
                far4_tools.pack_far4(Path(temp_dir,'mod_dump'),bigfart,save_key,bpr_hash)

def main(args: Sequence[str] = None):
    parser = argparse.ArgumentParser(description='Tool to install .mod files from toolkit/workbench to your bigfart or ps4 level backup, currently only installs as single levels, (.bins)')

    parser.add_argument("bigfart", help="Path to your bigfart save file or L0 ps4 level backup")
    parser.add_argument('-m','--mods',action='append',help="Path to a mod file you want to install, call -m mutiple times for mutiple mods",required=True)
    
    parser.add_argument('-i', '--ignore_plans', help='Do you want to ignore plan files?',action='store_false')
    parser.add_argument('-p', '--ps4_l0_level_backup', help='Is the bigfart a L0 ps4 level backup?',action='store_true')
    
    args = parser.parse_args()
    
    
    install_mods_to_bigfart(Path(args.bigfart),[Path(modd) for modd in args.mods], install_plans = args.ignore_plans,is_ps4_level_backup = args.ps4_l0_level_backup)
 
if __name__ == '__main__':
    main()

