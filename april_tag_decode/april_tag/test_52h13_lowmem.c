#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <string>
#include <cstring>
#include <opencv2/opencv.hpp>

extern "C" {
#include "apriltag.h"
#include "tagStandard52h13.h"
#include "common/image_u8.h"
}

static image_u8_t* mat_to_image_u8(const cv::Mat& gray) {
    image_u8_t* img = image_u8_create(gray.cols, gray.rows);
    for (int y = 0; y < gray.rows; y++) {
        memcpy(&img->buf[y * img->stride], gray.ptr(y), gray.cols);
    }
    return img;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <video-file>\n", argv[0]);
        return 1;
    }

    const char* source = argv[1];

    cv::VideoCapture cap(source);
    if (!cap.isOpened()) {
        fprintf(stderr, "Could not open video source: %s\n", source);
        return 1;
    }

    apriltag_detector_t* td = apriltag_detector_create();
    td->nthreads = 3;
    td->quad_decimate = 10.0;
    td->quad_sigma = 0.0;
    td->refine_edges = 1;
    td->decode_sharpening = 0.25;

    apriltag_family_t* tf = tagStandard52h13_create();

    // Low-memory choice: only 1 bit of correction
    apriltag_detector_add_family_bits(td, tf, 1);

    const std::string win = "tagStandard52h13 low-mem test";
    cv::namedWindow(win, cv::WINDOW_NORMAL);
    cv::resizeWindow(win, 640, 360);

    cv::Mat frame, gray, display;
    while (true) {
        if (!cap.read(frame)) {
            break;
        }

        if (frame.empty()) {
            break;
        }

        if (frame.channels() == 3) {
            cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);
        } else {
            gray = frame;
        }

        image_u8_t* img = mat_to_image_u8(gray);
        zarray_t* detections = apriltag_detector_detect(td, img);

        int n = zarray_size(detections);

        display = frame.clone();

        for (int i = 0; i < n; i++) {
            apriltag_detection_t* det;
            zarray_get(detections, i, &det);

            printf("id=%d, hamming=%d, decision_margin=%.2f\n",
                   det->id, det->hamming, det->decision_margin);

            for (int j = 0; j < 4; j++) {
                cv::Point p1((int)det->p[j][0], (int)det->p[j][1]);
                cv::Point p2((int)det->p[(j + 1) % 4][0], (int)det->p[(j + 1) % 4][1]);
                cv::line(display, p1, p2, cv::Scalar(0, 255, 0), 2);
            }

            cv::putText(display,
                        "ID=" + std::to_string(det->id),
                        cv::Point((int)det->c[0], (int)det->c[1]),
                        cv::FONT_HERSHEY_SIMPLEX,
                        0.6,
                        cv::Scalar(0, 0, 255),
                        2);
        }

        cv::putText(display,
                    "Detections: " + std::to_string(n),
                    cv::Point(20, 30),
                    cv::FONT_HERSHEY_SIMPLEX,
                    0.8,
                    cv::Scalar(255, 0, 0),
                    2);

        apriltag_detections_destroy(detections);
        image_u8_destroy(img);

        // Shrink the shown image so the popup is visually smaller too
        cv::Mat small;
        cv::resize(display, small, cv::Size(), 0.6, 0.6);

        cv::imshow(win, small);
        int key = cv::waitKey(1);
        if (key == 27 || key == 'q') {
            break;
        }
    }

    apriltag_detector_destroy(td);
    tagStandard52h13_destroy(tf);
    cap.release();
    cv::destroyAllWindows();
    return 0;
}